import copy, unittest
from datetime import datetime, timezone
from test_live_integration import LiveIntegration
from test_dev_recovery import DevRecovery

class StoreRecovery(unittest.TestCase):
 read=LiveIntegration.read
 register=LiveIntegration.register
 invoke=LiveIntegration.invoke
 def fresh(self,call,config):
  result=DevRecovery.fresh(self,call,config)
  if call[0]=='voice':
   result.update(resolvedStage='live',resolvedPackageId='SolarAccountImageBuild1211',instanceId='one')
  return result
 def setUp(self):
  LiveIntegration.setUp(self)
  self.cfg={**self.g['live_values_config'](),'stage':'live','package_id':'SolarAccountImageBuild1211','presentation_token':'solaranlage-store-werte'}
  self.g['live_values_config']=lambda:self.cfg
  self.g['_values_config_reader']=lambda section:None
  self.event['context']['System']['user'].pop('accessToken')
  self.event['request']['presentationUri']='widget://'+self.skill+'_live/SolarAccountImageBuild1211/one'
  self.g['send_registration']=self.fresh
 def test_tokenless_store_open_uses_verified_instance_and_values(self):
  self.event['request']['arguments']=['solar.widget.text.open.v1']
  result=self.invoke()
  self.assertEqual(self.registrations[-1][0],'voice')
  self.assertEqual(self.registrations[-1][1]['stage'],'live')
  self.assertNotIn('instanceId',self.registrations[-1][1])
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-store-werte')
  self.assertNotIn('LinkAccount',str(result))
  self.assertEqual(self.calls,[])
 def test_tokenless_store_fullscreen_timer_preserves_instance_without_second_fetch(self):
  self.event['request'].pop('presentationUri')
  self.event['request']['token']='solaranlage-store-werte'
  self.event['request']['arguments']=['solar.fullscreen.live.auto.v1',int(datetime.now(timezone.utc).timestamp()*1000)+3600000,0,'one']
  result=self.invoke()
  self.assertEqual(self.registrations[-1][0],'voice')
  self.assertNotIn('instanceId',self.registrations[-1][1])
  self.assertIn('one',str(result['response']['directives'][0]['document']))
  self.assertTrue(result['response'].get('directives'))
  self.assertEqual(self.calls,[])
 def test_failed_store_timer_keeps_previous_display(self):
  self.g['send_registration']=lambda *a:(_ for _ in ()).throw(ValueError('verified_registration_required'))
  self.event['request'].pop('presentationUri')
  self.event['request']['token']='solaranlage-store-werte'
  self.event['request']['arguments']=['solar.fullscreen.live.auto.v1',int(datetime.now(timezone.utc).timestamp()*1000)+3600000,0,'one']
  self.assertEqual(self.invoke()['response'],{'shouldEndSession':True})
 def test_store_open_does_not_render_values_when_verification_fails(self):
  self.g['send_registration']=lambda *a:(_ for _ in ()).throw(ValueError('verified_registration_required'))
  self.event['request']['arguments']=['solar.widget.text.open.v1']
  result=self.invoke()
  self.assertFalse(any(d.get('type')=='Alexa.Presentation.APL.RenderDocument' for d in result['response'].get('directives',[])))
  self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
