import unittest
from test_live_integration import LiveIntegration
from test_dev_recovery import DevRecovery

class VoiceBound(unittest.TestCase):
 read=LiveIntegration.read
 register=LiveIntegration.register
 invoke=LiveIntegration.invoke
 fresh=DevRecovery.fresh
 def setUp(self):
  LiveIntegration.setUp(self)
  self.cfg={**self.g['live_values_config'](),'stage':'live','package_id':'SolarAccountImageBuild1211','presentation_token':'solaranlage-store-werte'}
  self.dev={**self.cfg,'stage':'development','package_id':'Solaranlage1811','presentation_token':'solaranlage-dev-1811','display_prefix':'DEV · '}
  self.g['live_values_config']=lambda:self.dev
  self.g['_values_config_reader']=lambda section:self.cfg if section=='store_values' else self.dev if section=='reveal_test_values' else None
  self.event['context']['System']['user'].pop('accessToken')
  self.event['request']={'type':'LaunchRequest','timestamp':'2026-11-20T18:00:00Z'}
 def answer(self,call,config):
  result=self.fresh(call,config)
  return {**result,'resolvedStage':'development','resolvedPackageId':'Solaranlage1811','instanceId':'one'}
 def test_tokenless_launch_renders_verified_current_device_data(self):
  self.g['send_registration']=self.answer
  result=self.invoke()
  self.assertEqual(self.registrations[-1][0],'voice')
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-store-werte')
  self.assertNotIn('LinkAccount',str(result));self.assertEqual(self.calls,[])
 def test_failed_device_verification_does_not_render_household_data(self):
  self.g['send_registration']=lambda *a:(_ for _ in ()).throw(ValueError('verified_registration_required'))
  result=self.invoke()
  self.assertFalse(any(d.get('type')=='Alexa.Presentation.APL.RenderDocument' for d in result['response'].get('directives',[])))
  self.assertEqual(self.calls,[])
 def test_present_invalid_token_does_not_use_device_fallback(self):
  self.event['context']['System']['user']['accessToken']='invalid'
  self.g['send_registration']=self.answer
  self.invoke();self.assertFalse(any(c[0]=='voice' for c in self.registrations))
 def test_unapproved_resolved_profile_is_not_rendered(self):
  self.g['send_registration']=lambda *a:{'registered':True,'binding':'c'*64,'snapshot':{'binding':'c'*64},'pv':{'power_w':123},'resolvedStage':'live','resolvedPackageId':'Other','instanceId':'one'}
  result=self.invoke();self.assertFalse(any(d.get('type')=='Alexa.Presentation.APL.RenderDocument' for d in result['response'].get('directives',[])))

if __name__=='__main__':unittest.main()
