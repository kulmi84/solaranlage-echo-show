import json
import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from pathlib import Path
from build_live_images import build_live


class LiveImageTests(unittest.TestCase):
    def setUp(self):
        self.scope = {'__file__': __file__}
        exec(compile(build_live(), 'image-beta', 'exec'), self.scope)

    def event(self, intent=None, token='a' * 64):
        return {'request': {'type': 'IntentRequest' if intent else 'LaunchRequest',
                            'intent': {'name': intent}},
                'context': {'System': {'user': {'accessToken': token},
                    'device': {'supportedInterfaces': {'Alexa.Presentation.APL': {}}}}}}

    def root(self, response):
        return response['response']['directives'][0]['document']['mainTemplate']['items'][0]

    def test_link_required_shows_no_fake_solar_values_and_retains_probes(self):
        result = self.scope['lambda_handler'](self.event(token=None), None)
        root = self.root(result)
        self.assertEqual(result['response']['card']['type'], 'LinkAccount')
        self.assertTrue(result['response']['shouldEndSession'])
        self.assertNotIn('3,20 kW', json.dumps(root))
        self.assertIn('tickProbe', json.dumps(root))
        self.assertIn('imageProbeStatus', json.dumps(root))

    def test_grant_builds_native_house_pilot_without_changing_clock(self):
        base = self.scope['IMAGE_ORIGIN'] + '/dashboard.png?s=' + 'x' * 100
        self.scope['create_image_session'] = lambda *_: {'base_url': base, 'expires_in': 3600}
        self.scope['image_config'] = lambda: {}
        result = self.scope['lambda_handler'](self.event(), None)
        root = self.root(result)
        pages = root['items'][0]['items']
        self.assertEqual(len(pages), 2)
        self.assertIn('/tile.png?s=', json.dumps(pages))
        self.assertIn('tile_live_0_1', json.dumps(pages))
        self.assertNotIn('liveValuesImage', json.dumps(pages))
        self.assertNotIn('a' * 64, json.dumps(result))
        self.assertNotIn('SendEvent', json.dumps(root['handleTick'][-1]))
        self.assertIn('60000', json.dumps(root['handleTick'][-1]))
        self.assertTrue(result['response']['shouldEndSession'])
        self.assertIn('clock.png', json.dumps(root))

    def test_failed_grant_does_not_expose_error_or_fake_readings(self):
        self.scope['image_config'] = lambda: {}
        self.scope['create_image_session'] = lambda *_: (_ for _ in ()).throw(ValueError('secret'))
        result = self.scope['lambda_handler'](self.event(), None)
        self.assertNotIn('3,20 kW', json.dumps(result))
        self.assertNotIn('secret', json.dumps(result))

    def test_solar_voice_uses_live_reader_not_static_demo(self):
        calls=[]
        def reader(url,token):
            calls.append((url,token))
            return {'metrics': {'home_w': 1731}, 'stale': False}
        self.scope['read_pv']=reader
        result=self.scope['lambda_handler'](self.event('ConsumptionIntent'),None)
        self.assertIn('1,73 Kilowatt', result['response']['outputSpeech']['text'])
        self.assertEqual(calls,[(self.scope['RELAY_URL'],'a'*64)])

    def test_stop_stays_silent(self):
        result=self.scope['lambda_handler'](self.event('AMAZON.StopIntent'),None)
        self.assertEqual(result['response'], {'shouldEndSession': True})

    def test_speaker_never_announces_static_demo_numbers(self):
        event = self.event()
        event['context']['System']['device']['supportedInterfaces'] = {}
        result=self.scope['lambda_handler'](event,None)
        self.assertIn('Echo Show',result['response']['outputSpeech']['text'])
        self.assertNotIn('3,20',json.dumps(result))

    def test_unexpected_apl_refresh_still_cannot_restore_demo_values(self):
        event=self.event(token=None)
        event['request']={'type':'Alexa.Presentation.APL.UserEvent','arguments':['refresh']}
        result=self.scope['lambda_handler'](event,None)
        self.assertNotIn('3,20 kW',json.dumps(result))


class StatusVoiceTests(unittest.TestCase):
    event = LiveImageTests.event
    # Run requests through the generated beta entry point and real reader.
    def setUp(self):
        self.scope = {"__file__": __file__}
        exec(compile(build_live(), "image-beta", "exec"), self.scope)
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now

        self.scope['datetime'] = FixedDateTime
        self.now = now
        self.payload = {
            'power_w': 3200, 'home_w': 731, 'battery_soc': 82,
            'today_pv_kwh': 12.34, 'grid_import_w': 0, 'grid_export_w': 2400,
            'local_date': '2026-10-25', 'energy_date': '2026-10-25',
            'received_at': (now - timedelta(seconds=125)).isoformat(),
        }
        self.scope['urlopen'] = self.fake_response
        self.scope['create_image_session'] = Mock(side_effect=AssertionError('No image grant for speech'))
        self.scope['image_config'] = Mock(side_effect=AssertionError('No display config for speech'))

    def fake_response(self, request, timeout):
        self.assertEqual(request.full_url, self.scope['RELAY_URL'])
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + 'a' * 64)
        raw = json.dumps(self.payload).encode()

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return raw[:limit]

        return Response()

    def status(self, apl=False):
        event = self.event('StatusIntent')
        if not apl:
            event['context']['System']['device']['supportedInterfaces'] = {}
        response = self.scope['lambda_handler'](event, None)['response']
        self.assertTrue(response['shouldEndSession'])
        self.assertNotIn('directives', response)
        return response['outputSpeech']['text']

    def test_status_reads_requested_metrics_and_age_on_both_device_types(self):
        for apl in (False, True):
            with self.subTest(apl=apl):
                speech = self.status(apl)
                for phrase in ('Leistung inklusive Balkonkraftwerk: 3,20 Kilowatt',
                        'Hausverbrauch: 731 Watt', 'Akkustand: 82 Prozent',
                        'Heutige Produktion inklusive Balkonkraftwerk: 12,34 Kilowattstunden',
                        'Netzbezug: 0 Watt', 'Einspeisung: 2,40 Kilowatt',
                        'Die Werte sind 2 Minuten und 5 Sekunden alt.'):
                    self.assertIn(phrase, speech)
                self.assertNotIn('veraltet', speech)
        self.scope['create_image_session'].assert_not_called()
        self.scope['image_config'].assert_not_called()

    def test_missing_optional_values_are_explicit_while_zero_stays_valid(self):
        self.payload.update(home_w=None, battery_soc=0, today_pv_kwh=None,
                            grid_export_w=None)
        speech = self.status()
        self.assertIn('Hausverbrauch: keine Daten vorhanden.', speech)
        self.assertIn('Akkustand: 0 Prozent.', speech)
        self.assertIn('Heutige Produktion inklusive Balkonkraftwerk: keine Daten vorhanden.', speech)
        self.assertIn('Einspeisung: keine Daten vorhanden.', speech)
        self.assertNotIn('—', speech)

    def test_stale_values_are_warned_once_and_age_is_precise(self):
        self.payload['received_at'] = (self.now - timedelta(seconds=240)).isoformat()
        speech = self.status()
        self.assertTrue(speech.startswith('Achtung, die Daten sind veraltet. Zuletzt gemeldeter Status.'))
        self.assertEqual(speech.count('veraltet'), 1)
        self.assertIn('Die Werte sind 4 Minuten alt.', speech)

    def test_previous_day_production_is_not_reported_as_today(self):
        self.payload['energy_date'] = '2026-10-24'
        speech = self.status()
        self.assertIn('Heutige Produktion inklusive Balkonkraftwerk: keine Daten vorhanden.', speech)
        self.assertNotIn('12,34', speech)

    def test_unlinked_status_does_not_fetch_or_create_images(self):
        self.scope['read_pv'] = Mock(side_effect=AssertionError('No unauthenticated read'))
        result = self.scope['lambda_handler'](self.event('StatusIntent', token=None), None)
        self.assertEqual(result['response']['card']['type'], 'LinkAccount')
        self.assertTrue(result['response']['shouldEndSession'])
        self.scope['read_pv'].assert_not_called()

    def test_connection_error_does_not_disclose_details_or_invent_values(self):
        self.scope['read_pv'] = Mock(side_effect=OSError('secret-token'))
        speech = self.status()
        self.assertIn('nicht verfuegbar', speech)
        self.assertNotIn('secret-token', speech)
        self.assertNotIn('0 Watt', speech)

    def test_invalid_readings_fail_closed(self):
        for key, value in (('power_w', float('nan')), ('battery_soc', 101),
                           ('grid_import_w', -1), ('home_w', True)):
            with self.subTest(key=key):
                previous = self.payload[key]
                self.payload[key] = value
                self.assertIn('nicht verfuegbar', self.status())
                self.payload[key] = previous

    def test_age_formatting_and_clock_skew(self):
        for age, expected in ((0, '0 Sekunden'), (1, '1 Sekunde'),
                (60, '1 Minute'), (3600, '1 Stunde'),
                (90061, '1 Tag und 1 Stunde und 1 Minute und 1 Sekunde')):
            with self.subTest(age=age):
                self.payload['received_at'] = (self.now - timedelta(seconds=age)).isoformat()
                self.assertIn('Die Werte sind ' + expected + ' alt.', self.status())
        self.payload['received_at'] = (self.now + timedelta(seconds=30)).isoformat()
        self.assertIn('Die Werte sind 0 Sekunden alt.', self.status())
        self.payload['received_at'] = (self.now + timedelta(seconds=61)).isoformat()
        self.assertIn('nicht verfuegbar', self.status())
        self.assertEqual(self.scope['spoken_status_age'](None), 'Das Alter der Werte ist nicht bekannt.')

    def test_test_model_exposes_status_without_modifying_production_model(self):
        beta_model = json.loads(Path(__file__).with_name('interaction-model.de-DE.json').read_text(encoding='utf8'))
        language = beta_model['interactionModel']['languageModel']
        self.assertEqual(language['invocationName'], 'meine solaranlage test')
        status = next(intent for intent in language['intents'] if intent['name'] == 'StatusIntent')
        self.assertIn('status', status['samples'])
        self.assertIn('nach dem status', status['samples'])
        production = json.loads((Path(__file__).resolve().parents[2] / 'alexa/interaction-model.de-DE.json').read_text(encoding='utf8'))
        self.assertNotIn('StatusIntent', [i['name'] for i in production['interactionModel']['languageModel']['intents']])


if __name__ == '__main__': unittest.main()
