import copy,json,time,unittest
from test_voice_bound import VoiceBound

class LivePresentation(VoiceBound):
 def test_live_widget_keeps_store_presentation_when_data_authority_is_dev(self):
  self.g['send_registration']=self.answer
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_live/SolarAccountImageBuild1211/one',arguments=['solar.widget.text.open.v1'])
  result=self.invoke();d=result['response']['directives'][0]
  self.assertEqual(d['token'],'solaranlage-store-werte')
  self.assertNotIn('DEV Â·',json.dumps(d,ensure_ascii=False))
  self.assertNotIn('"type": "Image"',json.dumps(d));self.assertEqual(self.calls,[])
 def test_three_store_timer_rounds_keep_live_view_and_read_verified_device_each_time(self):
  self.g['send_registration']=self.answer
  self.event['request']={'type':'Alexa.Presentation.APL.UserEvent','timestamp':'2026-11-20T20:00:00Z','token':'solaranlage-store-werte','arguments':['solar.fullscreen.live.auto.v1',int(time.time()*1000)+3600000,0,'dev-source-instance']}
  for round in range(3):
   d=self.invoke()['response']['directives'][0]
   self.assertEqual(self.registrations[-1][0],'voice')
   self.assertEqual(d['token'],'solaranlage-store-werte')
   self.assertNotIn('DEV Â·',json.dumps(d,ensure_ascii=False))
  self.assertEqual(len(self.registrations),3);self.assertEqual(self.calls,[])
 def test_store_timer_rejection_preserves_the_previous_values(self):
  self.g['send_registration']=lambda *a:(_ for _ in ()).throw(ValueError('verified_registration_required'))
  self.event['request']={'type':'Alexa.Presentation.APL.UserEvent','token':'solaranlage-store-werte','arguments':['solar.fullscreen.live.auto.v1',int(time.time()*1000)+3600000,0,'one']}
  self.assertEqual(self.invoke()['response'],{'shouldEndSession':True})
 def test_unknown_widget_cannot_spoof_the_store_timer_to_get_a_voice_read(self):
  self.g['send_registration']=self.answer
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_live/Unapproved/one',token='solaranlage-store-werte',arguments=['solar.fullscreen.live.auto.v1',int(time.time()*1000)+3600000,0,'one'])
  self.invoke();self.assertFalse(any(c[0]=='voice' for c in self.registrations))

class EntryIsolation(VoiceBound):
 def test_real_voice_never_invokes_historical_handler(self):
  self.g['send_registration']=self.answer
  self.g['_before_visual_retirement']=lambda *a:(_ for _ in ()).throw(AssertionError('historical voice path'))
  result=self.invoke()
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-store-werte')
 def test_dev_tap_keeps_its_dev_view_and_existing_refresh_path(self):
  self.g['send_registration']=self.fresh
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_development/Solaranlage1811/one',arguments=['solar.widget.text.open.v1'])
  result=self.invoke()
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-dev-1811')
  self.assertIn('DEV ·',json.dumps(result,ensure_ascii=False))
  self.assertEqual(self.registrations[-1][0],'refresh')
  self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
