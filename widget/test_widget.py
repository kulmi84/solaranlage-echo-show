import json
import unittest
from pathlib import Path
from unittest.mock import patch
from build_widget import document
from widget_adapter import route_widget, OPEN
from build_skill import build
import runpy


class WidgetTests(unittest.TestCase):
    def test_tap_opens_standard_experience(self):
        doc = document()
        action = doc['mainTemplate']['items'][0]['onPress'][0]
        self.assertEqual(action['flags']['interactionMode'], 'STANDARD')
        self.assertEqual(action['arguments'], [OPEN])
        self.assertNotIn('3,20', json.dumps(doc))

    def test_tap_preserves_linked_account_without_mutating_request(self):
        event = {'context': {'System': {'user': {'accessToken': 'test-token'}}},
                 'request': {'type': 'Alexa.Presentation.APL.UserEvent', 'arguments': [OPEN]}}
        calls = []
        route_widget(event, None, lambda e, c: calls.append(e))
        self.assertEqual(calls[0]['request']['type'], 'LaunchRequest')
        self.assertEqual(calls[0]['context'], event['context'])
        self.assertEqual(event['request']['type'], 'Alexa.Presentation.APL.UserEvent')

    def test_other_requests_unchanged(self):
        for request in [{'type': 'LaunchRequest'}, {'type': 'IntentRequest', 'intent': {'name': 'AMAZON.StopIntent'}},
                        {'type': 'Alexa.Presentation.APL.UserEvent', 'arguments': ['other']}]:
            event = {'request': request}
            self.assertIs(route_widget(event, None, lambda e, c: e), event)

    def test_lifecycle_registers_only_our_package_and_never_renders(self):
        calls = []
        for kind, action in [('UsagesInstalled','install'), ('UpdateRequest','install'), ('UsagesRemoved','remove')]:
            event = {'context':{'System':{'user':{'accessToken':'test-token'}}},
                'request': {'type': 'Alexa.DataStore.PackageManager.' + kind, 'payload': {'packageId':'SolarWidget'}}}
            result = route_widget(event, None, lambda e,c: self.fail('Unexpected dashboard'), lambda e,a: calls.append(a))
            self.assertEqual(result['response'], {'shouldEndSession':True})
            self.assertEqual(calls[-1], action)

    def test_integrated_tap_uses_real_final_dashboard_path(self):
        scope = {'__file__': __file__}
        exec(compile(build(), 'widget-candidate', 'exec'), scope)
        scope['image_config'] = lambda: {}
        scope['create_image_session'] = lambda *_: {'base_url':scope['IMAGE_ORIGIN']+'/dashboard.png?s='+'x'*100,
            'expires_in':86400,'local_date':'2026-10-23'}
        event = {'request':{'type':'Alexa.Presentation.APL.UserEvent','arguments':[OPEN]},
            'context':{'System':{'user':{'accessToken':'a'*64},'device':{'supportedInterfaces':{'Alexa.Presentation.APL':{}}}}}}
        result = scope['lambda_handler'](event, None)
        self.assertTrue(result['response']['shouldEndSession'])
        self.assertEqual(result['response']['directives'][0]['type'], 'Alexa.Presentation.APL.RenderDocument')
        self.assertNotIn('outputSpeech', result['response'])

    def test_tap_without_link_never_fakes_live_data(self):
        scope = {'__file__': __file__}
        exec(compile(build(), 'widget-candidate', 'exec'), scope)
        scope['image_config'] = lambda: {}
        event = {'request':{'type':'Alexa.Presentation.APL.UserEvent','arguments':[OPEN]},
            'context':{'System':{'device':{'supportedInterfaces':{'Alexa.Presentation.APL':{}}}}}}
        result = scope['lambda_handler'](event, None)
        self.assertEqual(result['response']['card']['type'], 'LinkAccount')

    def test_registration_failure_cannot_block_widget_dashboard_open(self):
        event = {'request': {'type':'Alexa.Presentation.APL.UserEvent','arguments':[OPEN]},
                 'context':{'System':{'user':{'accessToken':'test-token'}}}}
        def unavailable(*args):
            raise TimeoutError('not available')
        result = route_widget(event,None,lambda e,c:e,unavailable)
        self.assertEqual(result['request']['type'], 'LaunchRequest')

    def test_install_without_account_waits_for_first_tap_instead_of_failing(self):
        event = {'request':{'type':'Alexa.DataStore.PackageManager.UsagesInstalled','payload':{'packageId':'SolarWidget'}}}
        result = route_widget(event,None,lambda e,c:self.fail(),lambda e,a:self.fail())
        self.assertTrue(result['response']['shouldEndSession'])

    def test_existing_fullscreen_and_voice_responses_identical_to_saved_live_code(self):
        old = {'__file__':__file__}
        new = {'__file__':__file__}
        baseline = runpy.run_path(str(Path(__file__).parent.parent/'build_skill.py'))['build']()
        exec(compile(baseline,'production-v1.0.7','exec'),old)
        exec(compile(build(),'widget-candidate','exec'),new)
        for scope in [old,new]:
            scope['image_config'] = lambda: {}
            scope['create_image_session'] = lambda *_: {'base_url':'https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s='+'x'*100,
                'expires_in':86400,'local_date':'2026-10-23'}
            scope['read_pv'] = lambda *_: {'metrics':{'power_w':2300,'home_w':1200,'battery_soc':72,
                'today_pv_kwh':8.4,'today_grid_export_kwh':4.1},'ageSeconds':125,'stale':False}
        requests = [{'type':'LaunchRequest'}, {'type':'SessionEndedRequest'},
                    {'type':'Alexa.Presentation.APL.UserEvent','arguments':['unrelated']}] + [
            {'type':'IntentRequest','intent':{'name':name}} for name in [
                'AMAZON.StopIntent','AMAZON.CancelIntent','AMAZON.FallbackIntent','AMAZON.HelpIntent',
                'ProductionIntent','CurrentPowerIntent','BatteryIntent','ConsumptionIntent','TodayProductionIntent','TodayExportIntent','StatusIntent']]
        for linked in [True,False]:
            for apl in [True,False]:
                for request in requests:
                    event = {'request':request,'context':{'System':{'user':{'accessToken':'a'*64} if linked else {},
                        'device':{'supportedInterfaces':{'Alexa.Presentation.APL':{}} if apl else {}}}}}
                    with self.subTest(linked=linked,apl=apl,request=request):
                        with patch('time.time', return_value=1792785600):
                            self.assertEqual(new['lambda_handler'](event,None),old['lambda_handler'](event,None))


if __name__ == '__main__':
    unittest.main()
