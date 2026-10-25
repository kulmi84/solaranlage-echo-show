"""Status requests through the production build and authenticated real reader."""
import json
import unittest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
from pathlib import Path
from build_skill import build
import test_image_display

class StatusVoiceTests(unittest.TestCase):
    event = test_image_display.ImageDisplayTests.event
    # Run requests through the generated production entry point and real reader.
    def setUp(self):
        self.scope = {"__file__": __file__}
        exec(compile(build(), "production-status", "exec"), self.scope)
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
        self.assertIn('nicht verfügbar', speech)
        self.assertNotIn('secret-token', speech)
        self.assertNotIn('0 Watt', speech)

    def test_invalid_readings_fail_closed(self):
        for key, value in (('power_w', float('nan')), ('battery_soc', 101),
                           ('grid_import_w', -1), ('home_w', True)):
            with self.subTest(key=key):
                previous = self.payload[key]
                self.payload[key] = value
                self.assertIn('nicht verfügbar', self.status())
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
        self.assertIn('nicht verfügbar', self.status())
        self.assertEqual(self.scope['spoken_status_age'](None), 'Das Alter der Werte ist nicht bekannt.')

    def test_production_invocation_and_status_samples(self):
        model = json.loads(Path('alexa/interaction-model.de-DE.json').read_text(encoding='utf8'))
        language = model['interactionModel']['languageModel']
        self.assertEqual(language['invocationName'], 'meine solaranlage')
        status = next(i for i in language['intents'] if i['name'] == 'StatusIntent')
        self.assertIn('nach dem status', status['samples'])

