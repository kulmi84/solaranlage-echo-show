import unittest, tempfile, shutil, runpy, json, sys, copy

from pathlib import Path

HERE=Path(__file__).parent



class LiveIntegration(unittest.TestCase):

 def setUp(self):

  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)

  root=Path(self.tmp.name)

  for file in ('lambda_function.py','skill_registration.py'):

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

 def test_initial_widget_mount_registers_and_sets_text_without_fullscreen(self):

  result=self.invoke();self.assertEqual(len(self.registrations),1);self.assertEqual(self.calls,[])

  self.assertEqual(result['response']['directives'][0]['type'],'Alexa.Presentation.APL.ExecuteCommands')

  self.assertEqual(result['response']['directives'][0]['commands'][-1]['value']['solar'],'123 W')

 def test_tap_opens_live_fullscreen_with_one_read_and_no_images(self):

  self.event['request']['arguments']=['solar.widget.text.open.v1']

  d=self.invoke()['response']['directives'][0]

  self.assertEqual(d['token'],'solaranlage-live-werte');self.assertEqual(len(self.calls),1)

  self.assertNotIn('"type": "Image"',json.dumps(d));self.assertNotIn('DEV ·',json.dumps(d))

  self.assertIn('solar.fullscreen.live.auto.v1',json.dumps(d))

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

  self.assertEqual(self.invoke()['response'],{})

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

   if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}

   if isinstance(value,list):return [normalize(v) for v in value]

   if isinstance(value,str):

    return value.replace('solar.fullscreen.live.auto.v1','solar.fullscreen.text.auto.v1').replace('1.1.0 (Build 1611)','DEV · 1.1.0 (Build 1611.11)')

   return value

  self.assertEqual(normalize(live),dev)



if __name__=='__main__':unittest.main()


class WidgetTemplateTests(unittest.TestCase):
 def test_visual_tree_matches_confirmed_dev(self):
  import copy
  dev=json.loads((HERE/'../../experiments/direct-values-dev/widget/documents/document.json').resolve().read_text(encoding='utf-8-sig'))
  live=json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf-8'))
  # Only compare visual components: registration, data binding and version text intentionally differ.
  def normalize(v):
   if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
   if isinstance(v,list):return [normalize(x) for x in v]
   if isinstance(v,str) and v.startswith('DEV '):return '1.1.0 (Build 1611)'
   return v
  self.assertEqual(live['mainTemplate']['items'][0]['items'],normalize(dev['mainTemplate']['items'][0]['items']))
 def test_mount_and_retry_stop_after_registration(self):
  doc=json.loads((HERE/'widget-template/documents/document.json').read_text())
  root=doc['mainTemplate']['items'][0]
  self.assertEqual(root['onMount'][0]['arguments'],['solar.widget.values.register.v1'])
  self.assertTrue(any(tick['when']=='${!registrationConfirmed}' for tick in root['handleTick']))


class WakeRefreshTests(unittest.TestCase):
 def test_wake_pending_is_set_when_hidden_and_consumed_before_request(self):
  doc=json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf-8'))
  change=doc['onDisplayStateChange'][0]
  self.assertEqual(change['when'],'${event.displayState == "hidden"}')
  tick=doc['mainTemplate']['items'][0]['handleTick'][0]
  self.assertEqual(tick['minimumDelay'],1000)
  self.assertIn('displayState != "hidden"',tick['when'])
  self.assertEqual(tick['commands'][0]['property'],'wakeRefreshPending')
  self.assertFalse(tick['commands'][0]['value'])
  self.assertEqual(tick['commands'][-1]['arguments'],['solar.widget.values.register.v1'])
 def test_regular_retry_interval_is_unchanged(self):
  doc=json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf-8'))
  retries=[t for t in doc['mainTemplate']['items'][0]['handleTick'] if t['when']=='${!registrationConfirmed}']
  self.assertEqual(len(retries),1);self.assertEqual(retries[0]['minimumDelay'],60000)
