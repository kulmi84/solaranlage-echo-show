import unittest
from unittest.mock import patch
import lambda_function as skill


class TapRefreshTests(unittest.TestCase):
    def event(self, request):
        return {'context': {'System': {'application': {'applicationId':
            'amzn1.ask.skill.6a7a8591-1eb6-42cf-b514-e1d0d056c4a2'}}}, 'request': request}

    @patch.object(skill, 'refresh_widget', return_value=True)
    def test_tap_refreshes_silently(self, refresh):
        response = skill.lambda_handler(self.event({'type': 'Alexa.Presentation.APL.UserEvent',
            'arguments': [skill.REFRESH_EVENT]}), None)
        refresh.assert_called_once_with()
        self.assertEqual(response['response'], {'shouldEndSession': True})

    @patch.object(skill, 'refresh_widget')
    def test_voice_and_unrelated_events_do_not_refresh(self, refresh):
        for request in [{'type': 'LaunchRequest'}, {'type': 'IntentRequest'},
                        {'type': 'Alexa.Presentation.APL.UserEvent', 'arguments': ['other']}]:
            response = skill.lambda_handler(self.event(request), None)
            self.assertNotIn('outputSpeech', response['response'])
        refresh.assert_not_called()

    @patch.object(skill, 'refresh_widget')
    def test_wrong_skill_is_rejected_before_network(self, refresh):
        with self.assertRaises(ValueError):
            skill.lambda_handler({'request': {'type': 'LaunchRequest'}}, None)
        refresh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
