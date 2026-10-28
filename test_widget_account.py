import copy, importlib.util, json, unittest
from pathlib import Path
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('account',root/'widget_account.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class WidgetAccountTest(unittest.TestCase):
    def event(self):
        return {'request':{'type':'Alexa.Presentation.APL.UserEvent','arguments':[m.WIDGET_ACCOUNT_EVENT],
            'presentationUri':'widget://'+m.WIDGET_ACCOUNT_SKILL+'/SolarImageStatus102/instance-1'},
            'context':{'System':{'application':{'applicationId':m.WIDGET_ACCOUNT_SKILL},'user':{'accessToken':'test-account'}}}}
    def route(self,e,session=None):
        return m.route_widget_account(e,None,lambda e,c:{'original':True},session or (lambda access,config:{'base_url':'https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s='+'a'*80,'expires_in':86400}),lambda:{},lambda e:e['context']['System']['user'].get('accessToken'))
    def test_silent_bootstrap(self):
        e=self.event();original=copy.deepcopy(e);r=self.route(e)['response'];self.assertEqual(e,original)
        self.assertTrue(r['shouldEndSession']);self.assertNotIn('outputSpeech',r)
        d=r['directives'][0];self.assertEqual(d['type'],'Alexa.Presentation.APL.ExecuteCommands');self.assertEqual(d['presentationUri'],e['request']['presentationUri'])
        values={c['property']:c['value'] for c in d['commands']};self.assertIn('/widget/value.png?s=',values['imageBase']);self.assertTrue(values['grantReady'])
    def test_development_presentation_uri_uses_same_account(self):
        e=self.event();e['request']['presentationUri']=e['request']['presentationUri'].replace(m.WIDGET_ACCOUNT_SKILL+'/',m.WIDGET_ACCOUNT_SKILL+'_development/')
        r=self.route(e)['response'];self.assertEqual(r['directives'][0]['presentationUri'],e['request']['presentationUri'])
        self.assertTrue(any(c.get('property')=='grantReady' and c['value'] is True for c in r['directives'][0]['commands']))
    def test_arbitrary_stage_suffix_is_rejected(self):
        e=self.event();e['request']['presentationUri']=e['request']['presentationUri'].replace(m.WIDGET_ACCOUNT_SKILL+'/',m.WIDGET_ACCOUNT_SKILL+'_other/')
        self.assertNotIn('directives',self.route(e)['response'])
    def test_unrelated_requests_pass_through(self):
        for request in [{'type':'LaunchRequest'},{'type':'IntentRequest','intent':{'name':'StatusIntent'}}]:
            self.assertEqual(self.route({'request':request}),{'original':True})
    def test_wrong_skill_and_presentation_rejected_before_access(self):
        for mutate in [lambda e:e['request'].update(presentationUri='widget://other/SolarImageStatus102/1'),lambda e:e['context']['System']['application'].update(applicationId='other')]:
            e=self.event();mutate(e);r=self.route(e,lambda *a:self.fail('must not create grant'));self.assertNotIn('directives',r['response'])
    def test_widget_tap_opens_existing_fullscreen(self):
        e=self.event();e['request']['arguments']=['solar.widget.open.v1'];old=copy.deepcopy(e)
        result=m.route_widget_account(e,None,lambda event,context:event['request']['type'],None,None,None)
        self.assertEqual(result,'LaunchRequest');self.assertEqual(e,old)
    def test_public_combined_builder(self):
        from build_skill import build
        scope={'__file__':str(root/'dist/lambda_function.py')};exec(compile(build(),'combined','exec'),scope)
        scope['image_config']=lambda:{}
        scope['create_image_session']=lambda *a:{'base_url':'https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s='+'a'*80,'expires_in':86400}
        response=scope['lambda_handler'](self.event(),None)['response']
        self.assertEqual(response['directives'][0]['type'],'Alexa.Presentation.APL.ExecuteCommands')
        self.assertNotIn('outputSpeech',response)
    def test_missing_link(self):
        e=self.event();e['context']['System']['user']={};r=self.route(e)['response'];self.assertEqual(len(r['directives'][0]['commands']),1);self.assertNotIn('outputSpeech',r)
    def test_failure_preserves_existing_urls(self):
        def fail(*a):raise RuntimeError('offline')
        cmds=self.route(self.event(),fail)['response']['directives'][0]['commands'];self.assertEqual([c['property'] for c in cmds],['accountMessage'])
    def test_package_contains_no_private_source_and_renews(self):
        doc=json.loads((root/'experiments/widget-image/document.template.json').read_text());s=json.dumps(doc);self.assertNotIn('?k=',s);self.assertNotIn('?s=',s);self.assertNotIn('__PRIVATE',s)
        self.assertEqual(doc['onMount'][0]['flags'],{'interactionMode':'INLINE'})
        self.assertEqual(doc['mainTemplate']['items'][0]['items'][0]['onPress'][0]['flags'],{'interactionMode':'STANDARD'})
        self.assertIn('grantRefreshAt',s);self.assertIn('widgetAccount',s)
if __name__=='__main__':unittest.main()

