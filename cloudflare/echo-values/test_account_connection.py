import copy
import json
import subprocess
import tempfile
from pathlib import Path
from test_connection_backoff import ConnectionBackoff
from skill.skill_registration import registration_requests

HERE=Path(__file__).parent

class AccountConnection(ConnectionBackoff):
    def v2(self):
        self.prepare_store()
        self.event['request']['arguments'][1]['connectionVersion']=2

    def state_answer(self, state, revision=1000):
        return {'registered':False,'connection':{'key':'connection-'+'d'*64,'state':state,'revision':revision}}

    def stop_commands(self):
        self.v2()
        self.g['send_registration']=lambda *a:self.state_answer('unlinked')
        return self.invoke()['response']['directives'][0]['commands']

    def test_confirmed_status_stops_but_no_measurements_or_speech_are_returned(self):
        commands=self.stop_commands()
        state=next(c['value'] for c in commands if c.get('property')=='connectionReplyState')
        self.assertEqual(state['state'],'unlinked')
        self.assertIs(state['verified'],False)
        self.assertFalse(any('when' in c for c in commands))
        self.assertFalse(any(c.get('property')=='snapshot' for c in commands))

    def test_unknown_invalid_response_and_401_never_pause(self):
        for response in [self.state_answer('unlinked',True),self.state_answer('unlinked',-1),
                         {'registered':False,'connection':{'state':'unlinked','revision':1000,'key':'snapshot'}}]:
            self.v2();self.g['send_registration']=lambda *a:response
            self.assertNotIn('"connectionReplyState"',json.dumps(self.invoke()))
        self.v2();self.g['send_registration']=lambda *a:(_ for _ in ()).throw(ValueError('verified_registration_required'))
        self.assertNotIn('"connectionReplyState"',json.dumps(self.invoke()))

    def test_v2_is_forwarded_only_for_exact_store_profile(self):
        self.v2();calls=registration_requests(self.event,self.cfg)
        self.assertEqual(calls[0][1]['connectionVersion'],2)
        event=copy.deepcopy(self.event)
        event['request']['presentationUri']='widget://'+self.skill+'_development/Solaranlage1811/one'
        calls=registration_requests(event,self.dev)
        self.assertNotIn('connectionVersion',calls[0][1])

    def test_actual_handler_and_document_stop_and_automatic_resume(self):
        stop=self.stop_commands()
        def linked(call,cfg):
            return {**self.fresh(call,cfg),'connection':self.state_answer('linked',2000)['connection']}
        self.g['send_registration']=linked
        success=self.invoke()['response']['directives'][0]['commands']
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/'commands.json';fixture.write_text(json.dumps({'stop':stop,'success':success}),encoding='utf8')
            result=json.loads(subprocess.check_output(['node',str(HERE/'connection-state-check.mjs'),str(HERE/'widget-template/documents/document.json'),str(fixture)],encoding='utf8'))
        self.assertEqual(result['pausedRequests'],0)
        self.assertTrue(result['scopedWake']);self.assertTrue(result['staleWakeRejected'])
        self.assertTrue(result['originalTimestamp']);self.assertTrue(result['resumedMinute'])

    def test_control_objects_never_overwrite_snapshot_binding(self):
        doc=json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf8'))
        for handler in ('DataStore:OnObjectReceived','DataStore:OnObjectChanged'):
            snapshot=next(c for c in doc[handler] if c.get('property')=='snapshot')
            self.assertIn("event.key == 'snapshot'",snapshot['when'])
        recovery=next(t for t in doc['mainTemplate']['items'][0]['handleTick'] if 'lastGoodSampleTime' in t['when'])
        self.assertIn('!linkPaused',recovery['when']);self.assertIn('!linkResumePending',recovery['when'])
