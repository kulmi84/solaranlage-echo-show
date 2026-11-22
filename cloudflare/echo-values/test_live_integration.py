import unittest, tempfile, shutil, runpy, json, sys, copy

from pathlib import Path

HERE=Path(__file__).parent



class LiveIntegration(unittest.TestCase):

 def setUp(self):

  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)

  root=Path(self.tmp.name)

  for file in ('lambda_function.py','skill_registration.py','support_trace.py','fullscreen_store.py'):

   shutil.copyfile(HERE/'skill'/file,root/file)

  config=json.loads((HERE/'skill'/'relay_config.example.json').read_text())

  config['live_values'].update(enabled=True,package_id='SyntheticLive',registration_secret='r'*40)

  (root/'relay_config.json').write_text(json.dumps(config))

  sys.path.insert(0,str(root));self.addCleanup(lambda:sys.path.remove(str(root)))

  self.ns=runpy.run_path(str(root/'lambda_function.py'));self.g=self.ns['lambda_handler'].__globals__

  self.calls=[];self.registrations=[]

  self.g['read_pv']=self.read

  self.g['send_registration']=self.register

  self.skill=config['live_values']['skill_id']

  self.event={'context':{'System':{'application':{'applicationId':self.skill},'user':{'userId':'amzn1.ask.account.synthetic','accessToken':'a'*64},'device':{'deviceId':'amzn1.ask.device.synthetic','supportedInterfaces':{'Alexa.Presentation.APL':{}}}}},'request':{'type':'Alexa.Presentation.APL.UserEvent','timestamp':'2026-11-16T15:00:00Z','presentationUri':'widget://'+self.skill+'/SyntheticLive/one','arguments':['solar.widget.values.register.v1']}}

 def register(self,call,config):

  self.registrations.append(call)

  return {'registered':True,'binding':'c'*64,'snapshot':{'binding':'c'*64,'solar':'123 W','home':'456 W','battery':'50 %','stamp':'Stand: original','sampleTime':123}}

 def read(self,url,token):

  self.calls.append(url);self.assertEqual(url,'https://solaranlage-echo-werte.kulmi84.workers.dev/v1/pv')

  self.assertEqual(token,'a'*64)

  return {'metrics':{'power_w':123,'home_w':456,'battery_soc':50},'valueText':'123 W','statusText':'Stand: original','stale':False}

 def invoke(self,event=None):return self.ns['lambda_handler'](event or self.event,None)

 def test_store_profile_keeps_dev_registration_separate(self):
  dev={**self.g['live_values_config'](),'stage':'development'}
  store={**dev,'stage':'live','package_id':'PublishedStore','presentation_token':'solaranlage-store-werte'}
  self.g['live_values_config']=lambda:dev
  self.g['_values_config_reader']=lambda section:store
  self.event['request']['presentationUri']='widget://'+self.skill+'_development/SyntheticLive/one'
  self.invoke()
  self.assertEqual(self.registrations[-1][1]['stage'],'development')
  self.event['request']['presentationUri']='widget://'+self.skill+'/PublishedStore/one'
  self.invoke()
  self.assertEqual(self.registrations[-1][1]['stage'],'live')
  self.assertEqual(self.registrations[-1][1]['packageId'],'PublishedStore')
  self.event['request']['arguments']=['solar.widget.text.open.v1']
  self.assertEqual(self.invoke()['response']['directives'][0]['token'],'solaranlage-store-werte')

 def test_initial_widget_mount_registers_and_sets_text_without_fullscreen(self):

  result=self.invoke();self.assertEqual(len(self.registrations),1);self.assertEqual(self.calls,[])
  self.assertIs(result['response'].get('shouldEndSession'), True)
  self.assertNotIn('outputSpeech',result['response'])

  self.assertEqual(result['response']['directives'][0]['type'],'Alexa.Presentation.APL.ExecuteCommands')

  self.assertEqual(result['response']['directives'][0]['commands'][0]['value']['solar'],'123 W')

 def test_immediate_display_uses_one_authenticated_snapshot_command(self):
  commands=self.invoke()['response']['directives'][0]['commands']
  self.assertEqual(len([c for c in commands if c['type']=='SetValue']),1)
  self.assertEqual(commands[0]['property'],'snapshot')
  self.assertEqual(commands[0]['value']['binding'],'c'*64)

 def test_inconsistent_household_binding_does_not_replace_last_values(self):
  self.g['send_registration']=lambda *args: {'registered':True,'binding':'d'*64,'snapshot':{'binding':'c'*64,'sampleTime':123}}
  response=self.invoke()['response']
  self.assertNotIn('directives',response)
  self.assertIs(response['shouldEndSession'],True)

 def test_small_widget_registration_failure_keeps_existing_values(self):
  self.g['send_registration']=lambda *args: (_ for _ in ()).throw(OSError('upstream unavailable'))
  response=self.invoke()['response']
  self.assertIs(response['shouldEndSession'],True)
  self.assertNotIn('directives',response)

 def test_pilot_stage_does_not_accept_live_package_uri(self):
  original=self.g['live_values_config']()
  self.g['live_values_config']=lambda:{**original,'stage':'development'}
  self.g['_before_live_values']=lambda *args:{'delegated':True}
  self.event['request']['presentationUri']='widget://'+self.skill+'_live/SyntheticLive/one'
  self.assertEqual(self.invoke(),{'delegated':True})
  self.assertEqual(self.registrations,[])

 def test_pilot_stage_registers_only_development_instance(self):
  original=self.g['live_values_config']()
  self.g['live_values_config']=lambda:{**original,'stage':'development'}
  self.event['request']['presentationUri']='widget://'+self.skill+'_development/SyntheticLive/one'
  self.invoke()
  self.assertEqual(self.registrations[0][1]['stage'],'development')

 def test_tap_opens_live_fullscreen_with_one_read_and_no_images(self):

  self.event['request']['arguments']=['solar.widget.text.open.v1']

  d=self.invoke()['response']['directives'][0]

  self.assertEqual(d['token'],'solaranlage-live-werte');self.assertEqual(len(self.calls),1)

  self.assertNotIn('"type": "Image"',json.dumps(d));self.assertNotIn('DEV ·',json.dumps(d))

  self.assertIn('solar.fullscreen.live.auto.v1',json.dumps(d))

 def test_voice_visual_intents_use_the_values_fullscreen_without_legacy_fallback(self):
  for name in ('RefreshIntent','AMAZON.NavigateHomeIntent'):
   with self.subTest(name=name):
    self.calls.clear();event=copy.deepcopy(self.event)
    event['request']={'type':'IntentRequest','intent':{'name':name}}
    self.g['_before_live_values']=lambda *args: (_ for _ in ()).throw(AssertionError('legacy visual fallback'))
    d=self.invoke(event)['response']['directives'][0]
    encoded=json.dumps(d)
    self.assertEqual(len(self.calls),1);self.assertEqual(d['token'],'solaranlage-live-werte')
    self.assertNotIn('"type": "Image"',encoded);self.assertNotIn('Aktualisieren',encoded)
    self.assertIn('Build',encoded);self.assertIn('solar.fullscreen.live.auto.v1',encoded)

 def test_existing_legacy_fullscreen_refresh_migrates_to_values(self):
  import time
  for args in (['refresh'],['auto_refresh',int(time.time()*1000)+60000,0]):
   with self.subTest(args=args):
    self.calls.clear();event=copy.deepcopy(self.event)
    event['request']={'type':'Alexa.Presentation.APL.UserEvent','token':'solaranlage','arguments':args}
    self.g['_before_live_values']=lambda *a: (_ for _ in ()).throw(AssertionError('legacy visual fallback'))
    d=self.invoke(event)['response']['directives'][0]
    encoded=json.dumps(d);self.assertEqual(len(self.calls),1)
    self.assertEqual(d['token'],'solaranlage-live-werte');self.assertNotIn('"type": "Image"',encoded)
    self.assertNotIn('Aktualisieren',encoded);self.assertIn('Build',encoded)

 def test_widget_with_legacy_fullscreen_token_does_not_bypass_package_scope(self):
  event=copy.deepcopy(self.event)
  event['request'].update(token='solaranlage',arguments=['refresh'],presentationUri='widget://'+self.skill+'/Unapproved/one')
  self.g['_before_live_values']=lambda *a:{'delegated':True}
  self.assertEqual(self.invoke(event),{'delegated':True});self.assertEqual(self.calls,[])

 def test_refresh_keeps_page_and_does_one_read(self):

  import time

  self.event['request'].update(arguments=['solar.fullscreen.live.auto.v1',int(time.time()*1000)+3600000,1],token='solaranlage-live-werte')

  d=self.invoke()['response']['directives'][0]['document']

  self.assertEqual(d['mainTemplate']['items'][0]['items'][0]['initialPage'],1);self.assertEqual(len(self.calls),1)

 def test_fullscreen_wake_uses_existing_refresh_on_current_page(self):
  self.event['request']={'type':'LaunchRequest'}
  doc=self.invoke()['response']['directives'][0]['document']
  root=doc['mainTemplate']['items'][0]
  self.assertEqual(doc['onDisplayStateChange'][0]['property'],'refreshAfterWake')
  tick=root['handleTick'][0]
  self.assertIn('refreshAfterWake || elapsedTime >= nextRefreshAt',tick['when'])
  self.assertFalse(tick['commands'][0]['value'])
  self.assertEqual(tick['commands'][-1]['arguments'][0],'solar.fullscreen.live.auto.v1')
  self.assertIn('currentPage',tick['commands'][-1]['arguments'][2])
 def test_refresh_failure_emits_no_overwrite(self):

  self.g['read_pv']=lambda *args:(_ for _ in ()).throw(OSError('offline'))

  import time

  self.event['request'].update(arguments=['solar.fullscreen.live.auto.v1',int(time.time()*1000)+3600000,0],token='solaranlage-live-werte')

  self.assertEqual(self.invoke()['response'],{'shouldEndSession':True})

 def test_disabled_skill_revokes_without_access_token(self):

  del self.event['context']['System']['user']['accessToken']

  self.event['request']['type']='AlexaSkillEvent.SkillDisabled'

  self.assertEqual(self.invoke()['response'],{});self.assertEqual(self.registrations[0][0],'unlink')

 def test_dev_package_falls_through_without_live_registration(self):

  self.event['request']['presentationUri']='widget://'+self.skill+'_development/DevPackage/one'

  self.g['_before_live_values']=lambda *args:{'kept':'DEV'}

  self.assertEqual(self.invoke(),{'kept':'DEV'});self.assertEqual(self.registrations,[])

 def test_fullscreen_layout_matches_dev_except_explicit_route_and_label(self):
  self.g['time']=type('FixedClock',(),{'time':staticmethod(lambda:1794841200)})

  self.event['request']={'type':'LaunchRequest'}

  live=self.invoke()['response']['directives'][0]['document']

  self.g['read_pv']=lambda *args:{'metrics':{'power_w':123,'home_w':456,'battery_soc':50},'valueText':'123 W','statusText':'Stand: original','stale':False}

  dev=self.g['native_handler'](self.event,None,dev_text=True)['response']['directives'][0]['document']

  def normalize(value):

   if isinstance(value,dict):
    if isinstance(value.get('text'),str) and '1.1.0 (Build ' in value['text']: value={**value,'text':'VERSION','fontSize':'VERSION_SIZE'}
    return {k:normalize(v) for k,v in value.items()}

   if isinstance(value,list):return [normalize(v) for v in value]

   if isinstance(value,str):

    return value.replace('solar.fullscreen.live.auto.v1','solar.fullscreen.text.auto.v1').replace('1.1.0 (Build 1711.2)','DEV · 1.1.0 (Build 1611.12)')

   return value

  self.assertEqual(normalize(live),normalize(dev))



if __name__=='__main__':unittest.main()


class WidgetTemplateTests(unittest.TestCase):
 def document(self):
  return json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf-8'))
 def test_visual_tree_matches_current_dev_except_dev_prefix(self):
  dev=json.loads((HERE/'dev-widget/documents/document.json').read_text(encoding='utf-8'))
  live=self.document()
  visual=lambda d:json.dumps(d['mainTemplate']['items'][0]['items'],ensure_ascii=False)
  # The authorized empty/error status changes only the timestamp slot.
  live_items=live['mainTemplate']['items'][0]['items'][0]['item']['items']
  dev_items=dev['mainTemplate']['items'][0]['items'][0]['item']['items']
  live_items[4]=copy.deepcopy(dev_items[4])
  self.assertEqual(visual(dev).replace('DEV \u00b7 1.1.0 (Build 2111)','1.1.0 (Build 2111)'),visual(live).replace('1.1.0 (Build 2211)','1.1.0 (Build 2111)'))
 def test_mount_fetch_and_refresh_deadline(self):
  root=self.document()['mainTemplate']['items'][0]
  event=[c for c in root['onMount'] if c['type']=='SendEvent']
  self.assertEqual(len(event),1)
  self.assertEqual(event[0]['arguments'][1]['trigger'],'mount')
  deadlines=[c['value'] for c in root['onMount'] if c.get('property')=='nextRefreshAt']
  self.assertEqual(deadlines,['${elapsedTime + retryDelayMs}'])
 def test_reveal_and_minute_are_separate_and_do_not_fire_hidden(self):
  doc=self.document();root=doc['mainTemplate']['items'][0]
  self.assertTrue(any(c.get('property')=='wakePending' and c['value'] is True for c in doc['onDisplayStateChange']))
  triggers=[]
  for tick in [t for t in root['handleTick'] if any(c.get('type')=='SendEvent' for c in t['commands'])]:
   self.assertIn('displayState != "hidden"',tick['when'])
   if any(c['type']=='SendEvent' for c in tick['commands']):
    self.assertTrue(any(c.get('property')=='nextRefreshAt' and c['value']=='${elapsedTime + retryDelayMs}' for c in tick['commands']))
   triggers.extend(c['arguments'][1]['trigger'] for c in tick['commands'] if c['type']=='SendEvent')
  self.assertEqual(triggers,['reveal','minute'])
  self.assertNotIn('"type": "Image"',json.dumps(doc))

