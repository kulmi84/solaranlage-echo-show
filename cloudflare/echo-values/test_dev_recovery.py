import copy, unittest
from datetime import datetime, timezone
from test_live_integration import LiveIntegration

class DevRecovery(unittest.TestCase):
 read=LiveIntegration.read
 register=LiveIntegration.register
 invoke=LiveIntegration.invoke
 def setUp(self):
  LiveIntegration.setUp(self)
  self.cfg={**self.g['live_values_config'](),'stage':'development','package_id':'Solaranlage1811','presentation_token':'solaranlage-dev-1811'}
  self.g['live_values_config']=lambda:self.cfg
  self.g['_values_config_reader']=lambda section:None
  self.event['context']['System']['user'].pop('accessToken')
  self.event['request']['presentationUri']='widget://'+self.skill+'_development/Solaranlage1811/one'
  self.g['send_registration']=self.fresh
 def fresh(self,call,config):
  self.registrations.append(call)
  return {'registered':True,'binding':'c'*64,'snapshot':{'binding':'c'*64,'solar':'123 W','home':'456 W','battery':'50 %','stamp':'fresh','sampleTime':123},'pv':{'power_w':123,'home_w':456,'battery_soc':50,'received_at':datetime.now(timezone.utc).isoformat(),'local_date':'2026-11-20','energy_date':'2026-11-20'}}
 def test_tokenless_dev_minute_uses_existing_registration(self):
  response=self.invoke()
  self.assertEqual(self.registrations[-1][0],'refresh')
  self.assertEqual(response['response']['directives'][0]['commands'][0]['value']['home'],'456 W')
  self.assertEqual(self.calls,[])
 def test_tokenless_dev_open_and_auto_keep_instance_scope(self):
  self.event['request']['arguments']=['solar.widget.text.open.v1']
  result=self.invoke()
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-dev-1811')
  self.assertIn('one',str(result['response']['directives'][0]['document']))
  auto=copy.deepcopy(self.event)
  auto['request'].pop('presentationUri')
  auto['request']['token']='solaranlage-dev-1811'
  auto['request']['arguments']=['solar.fullscreen.live.auto.v1',int(datetime.now(timezone.utc).timestamp()*1000)+3600000,0,'one']
  result=self.invoke(auto)
  self.assertEqual(self.registrations[-1][0],'refresh')
  self.assertEqual(self.registrations[-1][1]['instanceId'],'one')
  self.assertTrue(result['response'].get('directives'))
  self.assertEqual(self.calls,[])
 def test_failed_auto_preserves_display(self):
  self.g['send_registration']=lambda *args:(_ for _ in ()).throw(ValueError('verified_registration_required'))
  self.event['request'].pop('presentationUri')
  self.event['request']['token']='solaranlage-dev-1811'
  self.event['request']['arguments']=['solar.fullscreen.live.auto.v1',int(datetime.now(timezone.utc).timestamp())+3600,0,'one']
  self.assertEqual(self.invoke()['response'],{})

if __name__=='__main__':unittest.main()
