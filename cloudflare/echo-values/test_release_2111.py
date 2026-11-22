import unittest
import json
from test_voice_bound import VoiceBound

class RuntimeLabels(unittest.TestCase):
    setUp = VoiceBound.setUp
    read = VoiceBound.read
    register = VoiceBound.register
    fresh = VoiceBound.fresh
    answer = VoiceBound.answer
    invoke = VoiceBound.invoke

    def prepare_fallback_profiles(self):
        primary = {**self.dev, 'package_id': 'Solaranlage1711R2'}
        self.g['live_values_config'] = lambda: primary
        self.g['_values_config_reader'] = lambda section: None

    def test_actual_store_fallback_renders_2111_and_releases_voice(self):
        self.prepare_fallback_profiles()
        self.g['send_registration'] = self.answer
        result = self.invoke()
        self.assertIn('1.1.0 (Build 2211)', json.dumps(result))
        self.assertNotIn('DEV ·', json.dumps(result, ensure_ascii=False))
        self.assertEqual(result['response']['directives'][0]['token'], 'solaranlage-store-werte')
        self.assertIs(result['response']['shouldEndSession'], True)

    def test_actual_dev_fallback_shows_2111_and_releases_voice(self):
        self.prepare_fallback_profiles()
        self.g['send_registration'] = self.fresh
        self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',
            presentationUri='widget://'+self.skill+'_development/Solaranlage1811/one',
            arguments=['solar.widget.text.open.v1'])
        result = self.invoke()
        self.assertIn('DEV · 1.1.0 (Build 2111)', json.dumps(result, ensure_ascii=False))
        self.assertNotIn('Build 2311', json.dumps(result))
        self.assertEqual(result['response']['directives'][0]['token'], 'solaranlage-dev-1811')
        self.assertIs(result['response']['shouldEndSession'], True)
