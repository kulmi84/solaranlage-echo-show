"""Offline setup tests; no real HA/Cloudflare requests or credentials."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import installer

try:
    import yaml
    import jinja2
except ImportError:
    yaml = jinja2 = None


def mapping():
    return {key: 'sensor.test_' + key for key, *_ in installer.SENSORS}


class InstallerTests(unittest.TestCase):
    def test_urls_reject_plaintext_relay_embedded_credentials_and_query(self):
        for value in ['http://example.test/pv', 'https://user:secret@example.test/pv',
                      'https://example.test/pv?token=secret', 'https://example.test/pv#x',
                      'https://example.test/']:
            with self.subTest(url=value), self.assertRaises(ValueError):
                installer.endpoint(value, relay=True)
        self.assertEqual(installer.endpoint('https://example.test/pv', relay=True), 'https://example.test/pv')

    def test_mapping_rejects_injection_duplicate_energy_and_missing_primary(self):
        for mutate in [lambda m: m.update(home_w="sensor.x') }} INJECT"),
                       lambda m: m.update(power_w=''),
                       lambda m: m.update(energy_bkw=m['energy_pv'])]:
            data = mapping()
            mutate(data)
            with self.assertRaises(ValueError):
                installer.validate_mapping(data)

    def test_sensor_validation_reports_unit_state_and_statistics_issues(self):
        data = mapping()
        states = {entity: {'state': '0', 'attributes': {
            'unit_of_measurement': {'power': 'W', 'energy': 'kWh', 'percent': '%'}[kind],
            'state_class': 'total_increasing'}} for key, _, _, kind in installer.SENSORS
                  for entity in [data[key]]}
        self.assertEqual(installer.issues(data, states), [])
        states[data['power_w']]['state'] = 'unavailable'
        states[data['home_w']]['attributes']['unit_of_measurement'] = 'kWh'
        states[data['energy_pv']]['attributes']['state_class'] = 'measurement'
        states[data['battery_soc']]['state'] = '101'
        problems = installer.issues(data, states)
        self.assertEqual(sum(level == 'FEHLER' for level, _ in problems), 3)
        self.assertTrue(any(level == 'WARN' for level, _ in problems))

    def test_replacement_is_simultaneous(self):
        data = mapping()
        data['power_w'] = 'sensor.total_dc_power'
        result = installer.render_package(data)
        self.assertIn("'power_w': power('sensor.total_dc_power')", result)
        self.assertIn("'pv_dc_w': power('sensor.test_pv_dc_w')", result)

    def test_optional_metrics_are_not_silently_zero(self):
        data = {key: '' for key, *_ in installer.SENSORS}
        data['power_w'] = 'sensor.solar'
        result = installer.render_package(data)
        self.assertNotIn('recorder.get_statistics', result)
        self.assertIn("'today_pv_kwh': pv + bkw if pv is number and bkw is number else none", result)
        self.assertIn("'bkw_w': power('')", result)

    def test_separate_keys_and_no_existing_directory_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'new'
            installer.generate(out, mapping(), 'https://example.test/pv', 'solar-new',
                               '12345678-1234-1234-1234-123456789abc')
            keys = json.loads((out / 'relay/secrets.json').read_text())
            self.assertNotEqual(keys['READ_TOKEN'], keys['WRITE_TOKEN'])
            self.assertEqual(len(keys['READ_TOKEN']), 64)
            ha = (out / 'home-assistant/secrets-ergaenzen.yaml').read_text()
            alexa = (out / 'alexa/relay_config.json').read_text()
            self.assertNotIn(keys['READ_TOKEN'], ha)
            self.assertNotIn(keys['WRITE_TOKEN'], alexa)
            before = (out / 'alexa/relay_config.json').read_bytes()
            with self.assertRaises(FileExistsError):
                installer.generate(out, mapping(), 'https://example.test/pv', 'solar-new',
                                   '12345678-1234-1234-1234-123456789abc')
            self.assertEqual(before, (out / 'alexa/relay_config.json').read_bytes())
            self.assertNotIn('from beta_live_reader import', (out / 'alexa/lambda_function.py').read_text())

    def test_discovery_only_uses_get_and_does_not_persist_token(self):
        with patch('installer.get_json', return_value=[{'entity_id': 'sensor.solar'}]) as get:
            self.assertIn('sensor.solar', installer.load_states('https://ha.example.test', 'test-token'))
            get.assert_called_once_with('https://ha.example.test/api/states', 'test-token')

    def test_token_is_not_forwarded_on_redirect(self):
        self.assertIsNone(installer.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))

    def test_readonly_relay_check_has_meaningful_fresh_stale_missing_output(self):
        from datetime import datetime, timezone, timedelta
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'relay.json'
            config.write_text(json.dumps({'url': 'https://example.test/pv', 'read_token': 'test-secret'}))
            for age, code in [(0, 0), (300, 1)]:
                data = {'power_w': 0, 'received_at': (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()}
                output = io.StringIO()
                with patch('installer.get_json', return_value=data), contextlib.redirect_stdout(output):
                    self.assertEqual(installer.check_relay(config), code)
                self.assertNotIn('test-secret', output.getvalue())
                self.assertIn('Fehlende optionale Werte', output.getvalue())

    def test_http_error_is_actionable_and_redacted(self):
        from urllib.error import HTTPError
        with patch('installer.check_relay', side_effect=HTTPError('https://test?SECRET', 401, 'secret', {}, None)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(installer.main(['check', '--config', 'unused']), 1)
            self.assertIn('Token pruefen', output.getvalue())
            self.assertNotIn('SECRET', output.getvalue())

    def test_complete_offline_wizard_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'installation'
            answers = list(mapping().values()) + ['https://example.test/pv', 'solar-new',
                       '12345678-1234-1234-1234-123456789abc']
            output = io.StringIO()
            with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(output):
                self.assertEqual(installer.main(['wizard', '--out', str(out)]), 0)
            self.assertTrue((out / 'NAECHSTE-SCHRITTE.md').is_file())
            self.assertNotIn('READ_TOKEN', output.getvalue())
            with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(output):
                self.assertEqual(installer.main(['wizard', '--out', str(out)]), 1)
            self.assertIn('nichts wird ueberschrieben', output.getvalue())

    def test_configuration_error_does_not_hide_validation_reason(self):
        output = io.StringIO()
        with patch('builtins.input', side_effect=list(mapping().values()) + ['http://example.test/pv',
                  'solar-new', '12345678-1234-1234-1234-123456789abc']), contextlib.redirect_stdout(output):
            self.assertEqual(installer.main(['wizard', '--out', 'unused']), 1)
        self.assertIn('gueltige URL', output.getvalue())


@unittest.skipUnless(yaml and jinja2, 'Install requirements-test.txt for YAML/Jinja validation')
class GeneratedYamlTests(unittest.TestCase):
    def load(self, source):
        class Loader(yaml.SafeLoader):
            pass
        Loader.add_constructor('!secret', lambda loader, node: loader.construct_scalar(node))
        Loader.add_constructor('!input', lambda loader, node: {'input': loader.construct_scalar(node)})
        return yaml.load(source, Loader=Loader)

    def test_generated_full_and_partial_packages_parse(self):
        for data in [mapping(), {**{key: '' for key, *_ in installer.SENSORS}, 'power_w': 'sensor.solar'}]:
            package = self.load(installer.render_package(data))
            self.assertIn('pv_beta_upload', package['rest_command'])
            self.assertEqual(package['automation'][0]['mode'], 'single')
            self.assertEqual(package['automation'][0]['actions'][-1]['action'], 'rest_command.pv_beta_upload')

    def test_blueprint_all_inputs_bound_and_recorder_ids_templated(self):
        bp = self.load(installer.blueprint())
        self.assertEqual(bp['blueprint']['domain'], 'automation')
        self.assertEqual(set(bp['blueprint']['input']), set(mapping()))
        self.assertEqual(bp['variables']['power_w'], {'input': 'power_w'})
        self.assertEqual(bp['triggers'][0]['trigger'], 'time_pattern')
        self.assertEqual(bp['actions'][1]['data']['statistic_ids'][0], '{{ energy_pv }}')
        self.assertIn("power(power_w)", bp['actions'][-1]['data']['solar_data'])

    def test_generated_templates_compile(self):
        env = jinja2.Environment()
        for name in ['from_json', 'to_json']:
            env.filters[name] = lambda value: value
        for source in [installer.blueprint(), installer.render_package(mapping())]:
            data = self.load(source)
            def walk(item):
                if isinstance(item, dict):
                    for v in item.values(): walk(v)
                elif isinstance(item, list):
                    for v in item: walk(v)
                elif isinstance(item, str) and ('{{' in item or '{%' in item):
                    env.from_string(item)
            walk(data)


if __name__ == '__main__':
    unittest.main()
