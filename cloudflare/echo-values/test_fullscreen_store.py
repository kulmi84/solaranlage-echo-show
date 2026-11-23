import copy
import importlib
import json
import subprocess
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from test_voice_bound import VoiceBound

HERE = Path(__file__).parent


class FullscreenStore(VoiceBound):
    def dev_open(self):
        self.g['send_registration'] = self.fresh
        self.event['request'] = {'type': 'Alexa.Presentation.APL.UserEvent',
            'timestamp': '2026-11-21T12:00:00Z',
            'presentationUri': 'widget://' + self.skill + '_development/Solaranlage1811/one',
            'arguments': ['solar.widget.text.open.v1']}
        return self.invoke()

    def test_dev_closed_voice_uses_local_data_ticks_not_network_session(self):
        result = self.dev_open()
        self.assertIs(result['response']['shouldEndSession'], True)
        self.assertNotIn('reprompt', result['response'])
        self.assertNotIn('outputSpeech', result['response'])
        doc = result['response']['directives'][0]['document']
        self.assertEqual(doc['settings']['FullscreenStore']['dataBindings'][0]['namespace'], 'Solaranlage1811')
        self.assertNotIn('SendEvent', json.dumps(doc['mainTemplate']['items'][0]['handleTick']))
        self.assertNotIn('Image', json.dumps(doc))
        self.assertIn('FullscreenSnapshot.binding == "' + 'c' * 64 + '"', json.dumps(doc).replace('\\"', '"'))
        self.assertIn('FullscreenSnapshot.sampleTime >= fsSampleTime', str(doc))
        self.assertNotIn('FullscreenStore:OnObjectChanged', doc)
        self.assertNotIn('FullscreenStore:OnObjectReceived', doc)
        self.assertNotIn('FullscreenStore:WatchObject', str(doc))
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.registrations), 1)

    def test_store_and_voice_share_fix_but_keep_store_presentation(self):
        for source,namespace in (('development','Solaranlage1811'),('live','SolarAccountImagesV3')):
            def answer(call,config):
                result=self.fresh(call,config)
                return {**result,'resolvedStage':source,'resolvedPackageId':'Solaranlage1811' if source=='development' else 'SolarAccountImageBuild1211','instanceId':'one'}
            self.g['send_registration']=answer
            for request in ({'type':'LaunchRequest'}, {'type':'Alexa.Presentation.APL.UserEvent', 'presentationUri':'widget://'+self.skill+'_live/SolarAccountImageBuild1211/one', 'arguments':['solar.widget.text.open.v1']}):
                self.event['request']=request
                result=self.invoke()
                directive=result['response']['directives'][0]
                self.assertEqual(directive['token'],'solaranlage-store-werte')
                self.assertEqual(directive['document']['settings']['FullscreenStore']['dataBindings'][0]['namespace'],namespace)
                self.assertNotIn('DEV \u00b7',str(directive))
                self.assertIs(result['response']['shouldEndSession'],True)
                self.assertIn('solar.fullscreen.live.auto.v1',str(directive['document']['mainTemplate']['items'][0]['handleTick']))

    def test_three_live_binding_updates_and_error_preservation_in_component_scope(self):
        doc = self.dev_open()['response']['directives'][0]['document']
        fixture = HERE / 'binding-scope-fixture.json'
        fixture.write_text(json.dumps(doc), encoding='utf8')
        result = json.loads(subprocess.check_output(['node', str(HERE/'binding-scope-check.mjs'),
            str(fixture)], encoding='utf8'))
        self.assertEqual(result['successiveHomeValues'], ['601 W', '602 W', '603 W'])
        self.assertTrue(result['rejectedOlderSample'])
        self.assertTrue(result['rejectedOtherHouseholdBinding'])
        self.assertTrue(result['retainedAfterMissingData'])

    def test_store_missing_datastore_uses_three_bounded_fallback_rounds(self):
        def answer(call,config):
            return {**self.fresh(call,config),'resolvedStage':'live',
                    'resolvedPackageId':'SolarAccountImageBuild1211','instanceId':'one'}
        self.g['send_registration']=answer
        response=self.invoke()['response']
        self.assertIs(response['shouldEndSession'],True)
        self.assertNotIn('reprompt',response)
        fixture=HERE/'fullscreen-fallback-fixture.json'
        self.addCleanup(lambda: fixture.unlink(missing_ok=True))
        fixture.write_text(json.dumps(response['directives'][0]['document']),encoding='utf8')
        result=json.loads(subprocess.check_output(['node',str(HERE/'fullscreen-fallback-check.mjs'),str(fixture)],encoding='utf8'))
        self.assertTrue(all(result.values()))

    def test_rendered_geometry_text_and_navigation_match_before(self):
        # Compare a fully materialized initial document, not just selected styles.
        self.dev_open()  # module is imported from the isolated fixture directory
        module = importlib.import_module('fullscreen_store')
        with patch.object(module, 'attach', return_value=False):
            original = self.dev_open()['response']['directives'][0]['document']
        changed = self.dev_open()['response']['directives'][0]['document']
        root = changed['mainTemplate']['items'][0]
        values = {v['name']: v['value'] for v in root['bind']}
        def materialize(node):
            if isinstance(node, dict):
                for key, value in list(node.items()):
                    if key == 'text' and isinstance(value, str) and value.startswith('${fs'):
                        name, field = value[2:-1].split('.')
                        node[key] = values[name][field]
                    elif key == 'color' and value == '${fsLive.stale ? "#FFD166" : "#8FA8BC"}':
                        node[key] = '#FFD166' if values['fsLive']['stale'] else '#8FA8BC'
                    else: materialize(value)
            elif isinstance(node, list):
                for value in node: materialize(value)
        materialize(changed)
        for k in ('extensions', 'onMount', 'FullscreenStore:OnObjectReceived', 'FullscreenStore:OnObjectChanged'):
            changed.pop(k, None)
        changed['settings'].pop('FullscreenStore')
        root['bind'] = [b for b in root['bind'] if b['name'] not in ('fsLive','fsHistory','fsSampleTime','fsPending','nextHistoryAt')]
        root['handleTick'] = original['mainTemplate']['items'][0]['handleTick']
        self.assertEqual(changed, original)

    def test_worker_formatted_values_match_actual_python_renderer(self):
        now = int(time.time() * 1000)
        at = datetime.fromtimestamp(now / 1000, timezone.utc).isoformat()
        from zoneinfo import ZoneInfo
        local = datetime.fromtimestamp(now / 1000, ZoneInfo('Europe/Berlin'))
        metrics = {k: 2.675 for k in ('pv_dc_w','bkw_w','home_w','grid_import_w','grid_export_w',
            'battery_charge_w','battery_discharge_w','today_pv_kwh','today_home_kwh','today_grid_import_kwh',
            'today_grid_export_kwh','today_battery_charge_kwh','today_battery_discharge_kwh')}
        metrics.update(power_w=2345.5, battery_soc=12.5, energy_date=local.strftime('%Y-%m-%d'))
        history = {f'{prefix}_{key}_kwh': 12345.675 for prefix in ('month','year')
            for key in ('pv','home','grid_import','grid_export','battery_charge','battery_discharge')}
        history.update(month_id=local.strftime('%Y-%m'), year_id=local.strftime('%Y'))
        row = dict(live_json=json.dumps(metrics), live_at=at, timezone='Europe/Berlin',
            history_json=json.dumps(history), history_at=at)
        numbers = [[v,d,g] for v in (0, -0.0, 0.005, 1.005, 2.675, 2.5, 3.5, 999.995, 12345.675)
            for d in (0,2) for g in (False,True)]
        file = HERE / 'format-fixture.json'
        file.write_text(json.dumps(dict(row=row,now=now,numbers=numbers)), encoding='utf-8')
        formatted = json.loads(subprocess.check_output(['node', str(HERE/'format-fixtures.mjs'), str(file)], text=True, encoding='utf-8'))
        expected = [f'{v:,.{d}f}'.replace(',', '_').replace('.', ',').replace('_','.') if g
            else f'{v:.{d}f}'.replace('.', ',') for v,d,g in numbers]
        self.assertEqual(formatted['numbers'], expected)
        payload = {**metrics, 'received_at': at, 'received_local': local.strftime('%H:%M'),
                   'local_date': local.strftime('%Y-%m-%d'), 'history': {**history, 'received_at': at}}
        config = {**self.dev, '_fullscreen_store_namespace':'Solaranlage1811', '_fullscreen_store_snapshot': {'binding': 'c'*64, 'sampleTime': now}}
        result = self.g['native_handler'](self.event, None, dev_text=True, live_config=config, verified_pv=payload)
        values = {b['name']:b['value'] for b in result['response']['directives'][0]['document']['mainTemplate']['items'][0]['bind']}
        self.assertEqual(formatted['fullscreen']['live'], values['fsLive'])
        self.assertEqual(formatted['fullscreen']['history'], values['fsHistory'])


if __name__ == '__main__': unittest.main()
