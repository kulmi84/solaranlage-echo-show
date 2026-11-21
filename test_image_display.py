import json
import unittest
from build_skill import build

class ImageDisplayTests(unittest.TestCase):
    def setUp(self):
        self.scope={'__file__':__file__}
        exec(compile(build(),'v1.0.6','exec'),self.scope)
        self.scope['image_config']=lambda:{}
        self.scope['create_image_session']=lambda *_:{'base_url':self.scope['IMAGE_ORIGIN']+'/dashboard.png?s='+'x'*100,'expires_in':86400,'local_date':'2026-10-22'}
    def event(self,intent=None,token='a'*64):
        return {'request':{'type':'IntentRequest' if intent else 'LaunchRequest','intent':{'name':intent}},'context':{'System':{'user':{'accessToken':token},'device':{'supportedInterfaces':{'Alexa.Presentation.APL':{}}}}}}
    def test_final_layout_and_automatic_renewal(self):
        result=self.scope['lambda_handler'](self.event(),None)
        self.assertTrue(result['response']['shouldEndSession'])
        doc=result['response']['directives'][0]['document']
        self.assertEqual(doc['settings']['idleTimeout'],86400000)
        root=doc['mainTemplate']['items'][0]
        self.assertEqual(len(root['items'][0]['items']),2)
        encoded=json.dumps(doc)
        for forbidden in ['tickProbe','imageProbe','Testskill','Beta','TESTWERTE']:
            self.assertNotIn(forbidden,encoded)
        self.assertIn('tile_live_0_1',encoded)
        ticks = root['handleTick'][0]['commands']
        renewal = next(command for command in ticks if command['type'] == 'Sequential')
        self.assertIn('imageAccessExpiresAt - 300000', renewal['when'])
        self.assertIn('lastImageAccessRequest >= 60000', renewal['when'])
        self.assertEqual(renewal['commands'][1]['sequencer'], 'solarImageAccess')
        self.assertEqual(renewal['commands'][1]['arguments'], ['solar.fullscreen.renew.v1'])
        for page, interval in [('live', 60000), ('history', 21600000)]:
            status = next(command for command in ticks if command.get('componentId') == 'sharedStatus' + page)
            self.assertIn(f'>= {interval}', status['when'])
            self.assertIn('utcTime < imageAccessExpiresAt', status['when'])
            self.assertIn('statusImageBase', status['value'])
        self.assertNotIn('outputSpeech',result['response'])
    def test_renewal_updates_the_existing_document_and_rejects_wrong_tokens(self):
        event = self.event()
        event['request'] = {
            'type': 'Alexa.Presentation.APL.UserEvent',
            'arguments': ['solar.fullscreen.renew.v1'],
            'token': 'solaranlage',
            'source': {'id': 'solarRoot'},
        }
        event['context']['Alexa.Presentation.APL'] = {'token': 'solaranlage'}
        response = self.scope['lambda_handler'](event, None)['response']
        command = response['directives'][0]
        self.assertEqual(command['type'], 'Alexa.Presentation.APL.ExecuteCommands')
        self.assertEqual(command['token'], 'solaranlage')
        values = {item['property']: item['value'] for item in command['commands']}
        self.assertIn('/tile.png?', values['tileImageBase'])
        self.assertIn('/status.png?', values['statusImageBase'])
        self.assertGreater(values['imageAccessExpiresAt'], 0)
        event['request']['token'] = 'wrong-document'
        self.assertEqual(self.scope['lambda_handler'](event, None)['response'], {})

    def test_account_link_required_does_not_show_demo_values(self):
        result=self.scope['lambda_handler'](self.event(token=None),None)
        self.assertEqual(result['response']['card']['type'],'LinkAccount')
        self.assertNotIn('tile.png',json.dumps(result))
    def test_unavailable_grant_is_explicit_and_contains_no_private_details(self):
        self.scope['create_image_session']=lambda *_:(_ for _ in ()).throw(ValueError('SECRET'))
        result=self.scope['lambda_handler'](self.event(),None)
        self.assertIn('später',json.dumps(result,ensure_ascii=False))
        self.assertNotIn('SECRET',json.dumps(result))
    def test_solar_voice_reads_real_values(self):
        self.scope['read_pv']=lambda *_:{'metrics':{'home_w':1731},'stale':False}
        result=self.scope['lambda_handler'](self.event('ConsumptionIntent'),None)
        self.assertIn('1,73 Kilowatt',result['response']['outputSpeech']['text'])
    def test_stop_and_cancel_stay_silent(self):
        for intent in ['AMAZON.StopIntent','AMAZON.CancelIntent']:
            self.assertEqual(self.scope['lambda_handler'](self.event(intent),None)['response'],{'shouldEndSession':True})
    def test_fallback_retains_device_tested_original_behavior(self):
        self.assertEqual(self.scope['lambda_handler'](self.event('AMAZON.FallbackIntent'),None)['response'],{})

if __name__=='__main__':unittest.main()
