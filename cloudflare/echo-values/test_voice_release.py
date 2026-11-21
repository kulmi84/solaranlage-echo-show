import copy
import json
import time
import unittest
from unittest.mock import patch
from test_voice_bound import VoiceBound


class VoiceRelease(unittest.TestCase):
    setUp = VoiceBound.setUp
    read = VoiceBound.read
    register = VoiceBound.register
    fresh = VoiceBound.fresh
    answer = VoiceBound.answer
    invoke = VoiceBound.invoke

    def assert_released(self, result, token=None):
        response = result['response']
        self.assertIs(response.get('shouldEndSession'), True)
        self.assertNotIn('reprompt', response)
        self.assertNotIn('outputSpeech', response)
        self.assertNotIn('"type": "Finish"', json.dumps(response))
        if token:
            self.assertEqual(response['directives'][0]['token'], token)

    def test_voice_launch_closes_voice_without_changing_store_document(self):
        self.g['send_registration'] = self.answer
        with patch.object(self.g['time'], 'time', return_value=1795255200):
            before = self.g['_before_voice_release'](self.event, None)
            result = self.invoke()
        self.assert_released(result, 'solaranlage-store-werte')
        self.assertEqual(result['response']['directives'], before['response']['directives'])

    def test_dev_tap_and_store_tap_release_voice_and_keep_their_own_views(self):
        for package, stage, token, reader in (
            ('Solaranlage1811', 'development', 'solaranlage-dev-1811', self.fresh),
            ('SolarAccountImageBuild1211', 'live', 'solaranlage-store-werte', self.answer),
        ):
            with self.subTest(package=package):
                self.g['send_registration'] = reader
                self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',
                    presentationUri='widget://' + self.skill + '_' + stage + '/' + package + '/one',
                    arguments=['solar.widget.text.open.v1'])
                self.assert_released(self.invoke(), token)

    def test_three_fullscreen_refreshes_release_voice_without_losing_updates(self):
        self.g['send_registration'] = self.answer
        self.event['request'] = {'type': 'Alexa.Presentation.APL.UserEvent',
            'timestamp': '2026-11-21T10:00:00Z', 'token': 'solaranlage-store-werte',
            'arguments': ['solar.fullscreen.live.auto.v1', int(time.time()*1000)+3600000, 0, 'one']}
        for _ in range(3):
            self.assert_released(self.invoke(), 'solaranlage-store-werte')
        self.assertEqual(len(self.registrations), 3)
        self.assertEqual(self.calls, [])

    def test_failed_refresh_closes_voice_but_does_not_clear_last_display(self):
        self.g['send_registration'] = lambda *a: (_ for _ in ()).throw(ValueError('unavailable'))
        self.event['request'] = {'type': 'Alexa.Presentation.APL.UserEvent',
            'token': 'solaranlage-store-werte',
            'arguments': ['solar.fullscreen.live.auto.v1', int(time.time()*1000)+3600000, 0, 'one']}
        result = self.invoke()
        self.assert_released(result)
        self.assertNotIn('directives', result['response'])

    def test_fallback_ends_silently_instead_of_keeping_unknown_speech(self):
        self.event['request'] = {'type': 'IntentRequest', 'intent': {'name': 'AMAZON.FallbackIntent'}}
        self.assert_released(self.invoke())

    def test_session_end_and_lifecycle_responses_are_not_rewritten(self):
        for kind in ('SessionEndedRequest', 'AlexaSkillEvent.SkillDisabled'):
            event = copy.deepcopy(self.event)
            event['request'] = {'type': kind}
            before = self.g['_before_voice_release'](event, None)
            self.assertEqual(self.invoke(event), before)


if __name__ == '__main__':
    unittest.main()
