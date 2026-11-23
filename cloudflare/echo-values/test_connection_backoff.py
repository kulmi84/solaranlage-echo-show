import copy
import json
import unittest
import subprocess
from pathlib import Path
from test_voice_bound import VoiceBound
from skill.skill_registration import widget_trigger

HERE = Path(__file__).parent


class ConnectionBackoff(VoiceBound):
    def prepare_store(self, protocol=True):
        self.event['request'] = {
            'type': 'Alexa.Presentation.APL.UserEvent',
            'timestamp': '2026-11-22T12:00:00Z',
            'presentationUri': 'widget://' + self.skill + '_live/SolarAccountImageBuild1211/one',
            'arguments': ['solar.widget.values.register.v1', {
                'trigger': 'minute', 'shownElapsedMs': 0, 'sentElapsedMs': 60000,
                **({'connectionVersion': 1} if protocol else {})}]}

    def test_failed_registered_lookup_is_neutral_and_preserves_values(self):
        self.prepare_store()
        self.g['send_registration'] = lambda *a: (_ for _ in ()).throw(ValueError('verified_registration_required'))
        result = self.invoke()['response']
        self.assertIs(result['shouldEndSession'], True)
        self.assertNotIn('outputSpeech', result)
        self.assertNotIn('reprompt', result)
        commands = result['directives'][0]['commands']
        self.assertEqual({c['property'] for c in commands}, {'requestPending', 'connectionStatus'})
        self.assertEqual(commands[1]['value'], 'Verbindung pr\u00fcfen: Alexa-App')
        self.assertNotIn('Konto verkn', str(commands))

    def test_busy_delivery_retries_current_widget_without_auth_or_value_changes(self):
        self.prepare_store()
        self.g['send_registration']=lambda *a:{'registered':False,'deliveryBusy':True}
        result=self.invoke()['response']
        commands=result['directives'][0]['commands']
        self.assertIs(result['shouldEndSession'],True)
        self.assertNotIn('outputSpeech',result)
        self.assertNotIn('reprompt',result)
        self.assertFalse(any(c.get('property')=='snapshot' for c in commands))
        values={c.get('property'):c.get('value') for c in commands}
        self.assertEqual(values['nextRefreshAt'],'${elapsedTime + 5000}')
        self.assertEqual(values['retryDelayMs'],60000)

    def test_success_resets_backoff_without_second_read(self):
        self.prepare_store()
        self.g['send_registration'] = self.fresh
        result = self.invoke()['response']
        commands = result['directives'][0]['commands']
        self.assertEqual(commands[0]['property'], 'snapshot')
        self.assertEqual(commands[0]['value']['binding'], 'c' * 64)
        self.assertEqual(next(c['value'] for c in commands if c.get('property') == 'retryDelayMs'), 60000)
        self.assertEqual(next(c['value'] for c in commands if c.get('property') == 'connectionStatus'), '')
        self.assertEqual(len(self.registrations), 1)
        self.assertEqual(self.calls, [])

    def test_legacy_store_response_is_unchanged(self):
        self.prepare_store(protocol=False)
        self.g['send_registration'] = lambda *a: (_ for _ in ()).throw(ValueError('unavailable'))
        self.assertNotIn('directives', self.invoke()['response'])

    def test_dev_never_receives_store_retry_commands(self):
        self.prepare_store()
        self.event['request']['presentationUri'] = 'widget://' + self.skill + '_development/Solaranlage1811/one'
        self.g['send_registration'] = self.fresh
        result = self.invoke()
        self.assertNotIn('retryDelayMs', json.dumps(result))
        self.assertNotIn('connectionStatus', json.dumps(result))


class BackoffDocument(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((HERE/'widget-template/documents/document.json').read_text(encoding='utf8'))
        self.root = self.doc['mainTemplate']['items'][0]

    def test_lost_answers_are_throttled_before_send(self):
        paths = [self.root['onMount']] + [t['commands'] for t in self.root['handleTick'] if any(c['type'] == 'SendEvent' for c in t['commands'])]
        self.assertEqual(len(paths), 3)
        for commands in paths:
            send = next(i for i,c in enumerate(commands) if c['type'] == 'SendEvent')
            self.assertTrue(any(c.get('property') == 'nextRefreshAt' and c['value'] == '${elapsedTime + retryDelayMs}' for c in commands[:send]))
            self.assertTrue(any(c.get('property') == 'retryDelayMs' and c['value'] == '${Math.min(retryDelayMs * 2, 900000)}' for c in commands[:send]))
            self.assertEqual(commands[send]['arguments'][1]['connectionVersion'], 3)
        result = json.loads(subprocess.check_output(['node', str(HERE/'connection-backoff-check.mjs'),
            str(HERE/'widget-template/documents/document.json')], encoding='utf8'))
        self.assertEqual(result['missingReplies'], [0,60000,180000,420000,900000,1800000])
        self.assertEqual(result['explicitFailures'], result['missingReplies'])
        self.assertTrue(result['revealDidNotBypassBackoff'])
        self.assertTrue(result['datastoreRecoveryReset'])

    def test_reveal_cannot_bypass_failure_deadline_but_healthy_wake_remains_immediate(self):
        tick = next(t for t in self.root['handleTick'] if 'lastWakeAt' in t['when'])
        self.assertIn('!requestPending && retryDelayMs == 60000', tick['when'])
        self.assertIn('elapsedTime >= nextRefreshAt', tick['when'])
        self.assertIn('lastWakeAt + 3000', tick['when'])
        self.assertEqual(self.root['items'][0]['onPress'][0]['arguments'], ['solar.widget.text.open.v1'])

    def test_datastore_recovery_restores_normal_schedule_without_network_call(self):
        tick = next(t for t in self.root['handleTick'] if 'lastGoodSampleTime' in t['when'])
        self.assertIn('displaySnapshot.sampleTime > lastGoodSampleTime', tick['when'])
        self.assertFalse(any(c['type'] == 'SendEvent' for c in tick['commands']))
        self.assertEqual(next(c['value'] for c in tick['commands'] if c['property']=='retryDelayMs'),60000)

    def test_protocol_is_strict_and_does_not_infer_account_link_state(self):
        marker = {'trigger':'minute','shownElapsedMs':0,'sentElapsedMs':60000,'connectionVersion':1}
        self.assertEqual(widget_trigger(['solar.widget.values.register.v1',marker]), marker)
        for invalid in (True,0,4,'1'):
            with self.assertRaises(ValueError):
                widget_trigger(['solar.widget.values.register.v1',{**marker,'connectionVersion':invalid}])

    def test_original_timestamp_is_used_whenever_values_exist(self):
        stamp = self.root['items'][0]['item']['items'][4]['items'][0]
        self.assertIn('displaySnapshot.stamp ? displaySnapshot.stamp : connectionStatus', stamp['text'])
        self.assertIn('linkPaused', stamp['text'])
        self.assertIn('displaySnapshot.stamp', stamp['text'].split(': (displaySnapshot')[0])

    def test_technical_package_version_remains_nested_in_package_manifest(self):
        manifest = json.loads((HERE/'widget-template/manifest.json').read_text(encoding='utf8'))
        self.assertNotIn('version', manifest)
        self.assertEqual(manifest['manifest']['id'], 'SolarAccountImageBuild1211')
        self.assertEqual(manifest['manifest']['version'], '1.1.2')


if __name__ == '__main__':
    unittest.main()
