import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import json
import beta_live_reader
import beta_live_lambda


class FakeResponse:
    def __init__(self, data): self.data = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.data[:limit]


class LiveReaderTests(unittest.TestCase):
    def sample(self, power=0, age=0):
        return {'power_w': power, 'received_at': (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()}

    def test_zero_is_valid(self):
        with patch('beta_live_reader.urlopen', return_value=FakeResponse(self.sample())):
            self.assertEqual(beta_live_reader.read_pv('https://example.test/pv', 'read')['valueText'], '0,00 kW')

    def test_stale_value_is_marked(self):
        with patch('beta_live_reader.urlopen', return_value=FakeResponse(self.sample(2008, 240))):
            result = beta_live_reader.read_pv('https://example.test/pv', 'read')
            self.assertTrue(result['stale'])
            self.assertEqual(result['valueText'], '2,01 kW')

    def test_invalid_value_cannot_become_a_real_reading(self):
        for value in [True, None, '2000', -1, float('nan')]:
            with self.subTest(value=value), patch('beta_live_reader.urlopen', return_value=FakeResponse(self.sample(value))):
                with self.assertRaises(ValueError): beta_live_reader.read_pv('https://example.test/pv', 'read')

    def test_connection_failure_shows_no_value(self):
        event = {'request': {'type': 'LaunchRequest'}, 'context': {'System': {'device': {'supportedInterfaces': {'Alexa.Presentation.APL': {}}}}}}
        with patch('beta_live_lambda.read_pv', side_effect=OSError('unavailable')), patch('pathlib.Path.read_text', return_value='{"url":"https://example.test/pv","read_token":"read"}'):
            response = beta_live_lambda.lambda_handler(event, None)
        document = response['response']['directives'][0]['document']
        text = json.dumps(document, ensure_ascii=False)
        self.assertIn('Keine aktuellen Daten', text)
        self.assertNotIn('2,01', text)
        self.assertNotIn('OpenURL', text)

    def test_old_day_is_not_shown_as_today(self):
        data = self.sample(2500)
        data.update(energy_date='2020-01-01', today_pv_kwh=18.2, battery_soc=100, grid_import_w=0)
        with patch('beta_live_reader.urlopen', return_value=FakeResponse(data)):
            result = beta_live_reader.read_pv('https://example.test/pv', 'read')
        self.assertIsNone(result['metrics']['today_pv_kwh'])
        self.assertEqual(result['metrics']['battery_soc'], 100)
        self.assertEqual(result['metrics']['grid_import_w'], 0)

    def test_invalid_soc_is_rejected(self):
        data = self.sample(2500)
        data['battery_soc'] = 101
        with patch('beta_live_reader.urlopen', return_value=FakeResponse(data)):
            with self.assertRaises(ValueError):
                beta_live_reader.read_pv('https://example.test/pv', 'read')

    def test_today_metrics_keep_energy_units_and_nulls(self):
        data = self.sample(2500)
        data.update(energy_date='2026-10-17', local_date='2026-10-17', received_local='17:05',
                    today_pv_kwh=17.97, today_home_kwh=10.0, battery_soc=100,
                    battery_charge_w=0, home_w=None)
        with patch('beta_live_reader.urlopen', return_value=FakeResponse(data)):
            result = beta_live_reader.read_pv('https://example.test/pv', 'read')
        self.assertEqual(result['metrics']['today_pv_kwh'], 17.97)
        self.assertEqual(result['metrics']['battery_charge_w'], 0)
        self.assertIsNone(result['metrics']['home_w'])
        self.assertEqual(result['receivedText'], '17:05')


class AutomaticDisplayTests(unittest.TestCase):
    def event(self, arguments=None):
        request = {'type': 'LaunchRequest'} if arguments is None else {
            'type': 'Alexa.Presentation.APL.UserEvent', 'arguments': arguments}
        return {'request': request, 'context': {'System': {'device': {
            'supportedInterfaces': {'Alexa.Presentation.APL': {}}}}}}

    def render(self, seconds, event, power=2000):
        snapshot = {'metrics': {'power_w': power}, 'valueText': '2,00 kW',
                    'statusText': 'ok', 'stale': False, 'receivedText': '12:00'}
        with patch('beta_live_lambda.time.time', return_value=seconds), \
             patch('beta_live_lambda.read_pv', return_value=snapshot) as reader, \
             patch('pathlib.Path.read_text', return_value='{"url":"https://example.test/pv","read_token":"read"}'):
            response = beta_live_lambda.lambda_handler(event, None)
        return response, reader

    def document(self, response):
        return response['response']['directives'][0]['document']

    def test_auto_refresh_fetches_new_data_without_extending_hour(self):
        first, _ = self.render(1000, self.event())
        document = self.document(first)
        self.assertEqual(document['settings']['idleTimeout'], 3_600_000)
        tick = document['handleTick'][0]
        self.assertEqual(tick['minimumDelay'], 60_000)
        self.assertIn('foreground', tick['when'])
        command = tick['commands'][0]
        self.assertTrue(command['sequencer'])  # SendEvent must leave fast mode.
        response, reader = self.render(1060, self.event(command['arguments']), power=3100)
        reader.assert_called_once()
        updated = self.document(response)
        self.assertEqual(updated['settings']['idleTimeout'], 3_540_000)
        self.assertEqual(updated['handleTick'][0]['commands'][0]['arguments'], command['arguments'])
        self.assertIn('3,10 kW', json.dumps(updated))

    def test_touch_starts_new_hour(self):
        response, _ = self.render(1060, self.event(['refresh']))
        self.assertEqual(self.document(response)['settings']['idleTimeout'], 3_600_000)

    def test_display_never_requests_a_spoken_reply(self):
        for args in [None, ['refresh'], ['auto_refresh', 4_600_000]]:
            with self.subTest(arguments=args):
                response, _ = self.render(1060, self.event(args))
                self.assertNotIn('shouldEndSession', response['response'])
                self.assertNotIn('reprompt', response['response'])
                self.assertNotIn('outputSpeech', response['response'])
                self.assertEqual(response['response']['directives'][0]['type'],
                                 'Alexa.Presentation.APL.RenderDocument')

    def test_expired_automatic_event_stops_without_fetch(self):
        response, reader = self.render(4600, self.event(['auto_refresh', 4_600_000]))
        reader.assert_not_called()
        self.assertTrue(response['response']['shouldEndSession'])
        self.assertEqual(response['response']['directives'][0]['commands'], [{'type': 'Finish'}])

    def test_invalid_automatic_event_is_ignored(self):
        for args in [['auto_refresh', True], ['auto_refresh', 99_000_000], ['other'], 'refresh']:
            response, reader = self.render(1000, self.event(args))
            reader.assert_not_called()
            self.assertEqual(response['response'], {})


if __name__ == '__main__': unittest.main()
