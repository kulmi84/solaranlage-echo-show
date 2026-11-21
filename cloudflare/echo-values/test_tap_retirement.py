import copy,json,unittest
from test_voice_bound import VoiceBound

class TapRetirement(VoiceBound):
 def test_store_tap_uses_the_verified_device_reader_before_registration(self):
  self.g['send_registration']=self.answer
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_live/SolarAccountImageBuild1211/retired-binding',arguments=['solar.widget.text.open.v1'])
  self.g['registration_requests']=lambda *a:(_ for _ in ()).throw(AssertionError('must not require the retired instance binding'))
  result=self.invoke()
  self.assertEqual(self.registrations[-1][0],'voice')
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-store-werte')
  self.assertEqual(self.calls,[]);self.assertNotIn('"type": "Image"',json.dumps(result))
 def test_store_development_uri_keeps_its_stage_when_reading_the_exact_device(self):
  self.g['send_registration']=self.answer
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_development/SolarAccountImageBuild1211/one',arguments=['solar.widget.text.open.v1'])
  result=self.invoke();self.assertEqual(self.registrations[-1][0],'voice')
  self.assertEqual(self.registrations[-1][1]['stage'],'development')
  self.assertEqual(result['response']['directives'][0]['token'],'solaranlage-store-dev-werte')
 def test_unknown_widget_cannot_become_a_verified_voice_request(self):
  self.g['send_registration']=self.answer
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_live/Unapproved/one',arguments=['solar.widget.text.open.v1'])
  self.invoke();self.assertFalse(any(c[0]=='voice' for c in self.registrations))
 def test_old_image_fullscreen_is_replaced_by_the_values_entry(self):
  old={'version':'1.0','response':{'directives':[{'type':'Alexa.Presentation.APL.RenderDocument','token':'solaranlage','document':{'type':'APL','mainTemplate':{'item':{'type':'Image','source':'https://invalid.example/image.png'}}}}]}}
  expected={'version':'1.0','response':{'directives':[{'type':'Alexa.Presentation.APL.RenderDocument','token':'values','document':{'type':'APL','mainTemplate':{'item':{'type':'Text','text':'values'}}}}]}}
  self.g['_before_visual_retirement']=lambda *a:old
  self.g['_values_visual_entry']=lambda *a:expected
  self.assertEqual(self.invoke(),{**expected,'response':{**expected['response'],'shouldEndSession':True}})
 def test_retired_widget_cannot_bypass_uri_scope_to_restart_images(self):
  self.g['_before_visual_retirement']=lambda *a:{'version':'1.0','response':{'directives':[{'type':'Alexa.Presentation.APL.RenderDocument','token':'solaranlage','document':{}}]}}
  self.g['_values_visual_entry']=lambda *a:(_ for _ in ()).throw(AssertionError('widget scope bypass'))
  self.event['request'].update(type='Alexa.Presentation.APL.UserEvent',presentationUri='widget://'+self.skill+'_live/Unapproved/one')
  self.assertEqual(self.invoke()['response']['directives'],[])

if __name__=='__main__':unittest.main()
