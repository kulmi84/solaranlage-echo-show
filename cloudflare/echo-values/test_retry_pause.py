import copy
import json
import subprocess
import tempfile
from pathlib import Path
from test_connection_backoff import ConnectionBackoff
from skill.skill_registration import registration_requests

HERE=Path(__file__).parent

class RetryPause(ConnectionBackoff):
    def v3(self):
        self.prepare_store()
        self.event['request']['arguments'][1]['connectionVersion']=3

    def test_v3_handler_and_generated_root_pause_then_restart(self):
        self.v3();failures=[]
        for n in range(1,7):
            self.g['send_registration']=lambda *a:{'registered':False,'connection':{
                'state':'unknown','key':'connection-'+'d'*64,'revision':0,
                'retryPaused':n==6,'retryFailures':n}}
            response=self.invoke()['response']
            self.assertIs(response['shouldEndSession'],True)
            self.assertNotIn('outputSpeech',response);self.assertNotIn('reprompt',response)
            failures.append(response['directives'][0]['commands'])
        self.g['send_registration']=lambda call,cfg:{**self.fresh(call,cfg),'connection':{
            'state':'unknown','key':'connection-'+'d'*64,'revision':2000,'retryPaused':False,'retryFailures':0}}
        success=self.invoke()['response']['directives'][0]['commands']
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'replies.json';p.write_text(json.dumps({'failures':failures,'success':success}),encoding='utf8')
            result=json.loads(subprocess.check_output(['node',str(HERE/'retry-pause-check.mjs'),str(HERE/'widget-template/documents/document.json'),str(p)],encoding='utf8'))
            cached=json.loads(subprocess.check_output(['node',str(HERE/'retry-pause-check.mjs'),str(HERE/'widget-template/documents/document.json'),str(p),'cached'],encoding='utf8'))
            self.assertTrue(cached['cachedValuesNeverPaused'])
        self.assertEqual(result['attemptsBeforePause'],6);self.assertEqual(result['pausedRequests'],0)
        self.assertTrue(result['fullscreenWake']);self.assertTrue(result['originalTime']);self.assertTrue(result['resumedMinute'])

    def test_inconsistent_untrusted_pause_metadata_is_not_forwarded(self):
        self.v3()
        for invalid in ({'retryPaused':True,'retryFailures':1},{'retryPaused':True,'retryFailures':True},
                        {'retryPaused':True,'retryFailures':7},{'retryPaused':'true','retryFailures':6}):
            self.g['send_registration']=lambda *a:{'registered':False,'connection':{
                'state':'unknown','key':'connection-'+'d'*64,'revision':0,**invalid}}
            result=self.invoke()
            self.assertNotIn('"retryPaused"',json.dumps(result))

    def test_protocol3_never_goes_to_dev1811(self):
        self.v3();self.assertEqual(registration_requests(self.event,self.cfg)[0][1]['connectionVersion'],3)
        event=copy.deepcopy(self.event)
        event['request']['presentationUri']='widget://'+self.skill+'_development/Solaranlage1811/one'
        self.assertNotIn('connectionVersion',registration_requests(event,self.dev)[0][1])

    def test_fullscreen_launch_marks_wake_without_changing_response_or_speech(self):
        self.event['request']={'type':'LaunchRequest','timestamp':'2026-11-22T12:00:00Z'}
        self.g['send_registration']=self.answer
        result=self.invoke()['response']
        self.assertIs(self.registrations[-1][1]['resumeWidgetRetries'],True)
        self.assertEqual(result['directives'][0]['token'],'solaranlage-store-werte')
        self.assertIs(result['shouldEndSession'],True);self.assertNotIn('reprompt',result)

    def test_fullscreen_timer_and_dev_tap_do_not_mark_wake(self):
        self.event['request']={'type':'Alexa.Presentation.APL.UserEvent','timestamp':'2026-11-22T12:00:00Z',
            'token':'solaranlage-store-werte','arguments':['solar.fullscreen.live.auto.v1',0,'one']}
        self.g['send_registration']=self.answer;self.invoke()
        self.assertTrue(self.registrations)
        self.assertNotIn('resumeWidgetRetries',self.registrations[-1][1])
        self.event['request']={'type':'Alexa.Presentation.APL.UserEvent','timestamp':'2026-11-22T12:00:00Z',
            'presentationUri':'widget://'+self.skill+'_development/Solaranlage1811/one','arguments':['solar.widget.text.open.v1']}
        self.g['send_registration']=self.fresh;self.invoke()
        self.assertNotIn('resumeWidgetRetries',self.registrations[-1][1])
