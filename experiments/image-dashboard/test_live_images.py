import json
import unittest
from unittest.mock import patch
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


if __name__ == '__main__': unittest.main()
