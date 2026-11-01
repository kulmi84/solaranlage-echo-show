import copy,json,unittest
from build_skill import build
from pathlib import Path

class WidgetIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.scope={'__file__':__file__};exec(compile(build(),'built-skill','exec'),self.scope)
  self.scope['image_config']=lambda:{}
  self.scope['create_image_session']=lambda *_:{'base_url':self.scope['IMAGE_ORIGIN']+'/dashboard.png?s='+'x'*64,'expires_in':86400,'local_date':'2026-11-01'}
  self.writes=[];self.scope['widget_publish']=lambda d,c:self.writes.append((d,c))
  skill=self.scope['WIDGET_SKILL_ID']
  self.event={'request':{'type':'Alexa.Presentation.APL.UserEvent','arguments':['solar.widget.open.v1'],'presentationUri':'widget://'+skill+'_development/SolarAccountImage/fixture'},'context':{'System':{'application':{'applicationId':skill},'user':{'accessToken':'a'*64},'device':{'deviceId':'amzn1.ask.device.fixture','supportedInterfaces':{'Alexa.Presentation.APL':{}}}}}}
 def test_tap_republishes_current_account_then_opens_fullscreen(self):
  accounts=[];old=self.scope['create_image_session'];self.scope['create_image_session']=lambda a,c:accounts.append(a) or old(a,c)
  result=self.scope['lambda_handler'](self.event,None)
  self.assertEqual(len(self.writes),1);self.assertEqual(accounts,['a'*64,'a'*64]);self.assertEqual(result['response']['directives'][0]['type'],'Alexa.Presentation.APL.RenderDocument')
 def test_write_failure_does_not_block_fullscreen(self):
  self.scope['widget_publish']=lambda *_:(_ for _ in ()).throw(TimeoutError())
  self.assertEqual(self.scope['lambda_handler'](self.event,None)['response']['directives'][0]['type'],'Alexa.Presentation.APL.RenderDocument')
 def test_second_open_has_different_image_urls(self):
  a=json.dumps(self.scope['lambda_handler'](self.event,None));b=json.dumps(self.scope['lambda_handler'](self.event,None));self.assertNotEqual(a,b);self.assertNotIn('n=initial',a)
 def test_foreign_skill_cannot_publish(self):
  self.event['context']['System']['application']['applicationId']='amzn1.ask.skill.other'
  self.scope['lambda_handler'](self.event,None);self.assertFalse(self.writes)
 def test_generic_package_contains_no_private_grant(self):
  doc=json.loads(Path('alexa/widget/document.json').read_text(encoding='utf-8'));raw=json.dumps(doc)
  self.assertNotIn('?s=',raw);self.assertNotIn('123 W',raw);self.assertNotIn('PRIVAT',raw)
  self.assertEqual(doc['mainTemplate']['items'][0]['id'],'imageWidget')
 def test_package_and_runtime_match(self):
  manifest=json.loads(Path('alexa/widget/manifest.json').read_text(encoding='utf-8'))
  self.assertEqual(manifest['manifest']['id'],self.scope['WIDGET_PACKAGE_ID']);self.assertEqual(manifest['manifest']['version'],'2.0.1')
if __name__=='__main__':unittest.main()
