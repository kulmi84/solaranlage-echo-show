import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import installer
import setup_app


class DesktopSetupTests(unittest.TestCase):
    def test_provision_fresh_resources_and_current_history_without_shell(self):
        mapping = {key: 'sensor.test_' + key for key, *_ in installer.SENSORS}
        calls = []
        def run(args, **kwargs):
            self.assertNotIn('shell', kwargs)
            calls.append(args)
            command = args[3:]
            if command[0:2] == ['d1', 'create']:
                return SimpleNamespace(returncode=0, stdout='{"database_id":"12345678-1234-1234-1234-123456789abc"}')
            if command[0] == 'deploy':
                config = json.loads(Path(command[-1]).read_text())
                return SimpleNamespace(returncode=0, stdout='https://' + config['name'] + '.example.workers.dev')
            return SimpleNamespace(returncode=0, stdout='')
        with tempfile.TemporaryDirectory() as directory, patch('setup_app.shutil.which', return_value='npx'), patch('setup_app.subprocess.run', side_effect=run):
            out = Path(directory) / 'new'
            setup_app.cloud_setup(out, mapping, lambda _: None)
            config = json.loads((out / 'alexa/relay_config.json').read_text())
            self.assertTrue(config['url'].endswith('.example.workers.dev/pv'))
            self.assertNotIn('.invalid', (out / 'home-assistant/secrets-ergaenzen.yaml').read_text())
            history = (out / 'home-assistant/pv_history.yaml').read_text()
            self.assertIn('sensor.test_energy_pv', history)
            self.assertNotIn('sensor.total_pv_generation', history)
            self.assertIn('solarPager', (out / 'alexa/lambda_function.py').read_text())
            self.assertIn('solar_history', (out / 'relay/schema.sql').read_text())
            with self.assertRaises(installer.SetupError):
                setup_app.cloud_setup(out, mapping, lambda _: None)
            self.assertEqual(len(calls), 5)

    def test_failed_cloud_step_does_not_expose_vendor_output_or_create_files(self):
        mapping = {key: 'sensor.test_' + key for key, *_ in installer.SENSORS}
        with tempfile.TemporaryDirectory() as directory, patch('setup_app.shutil.which', return_value='npx'), patch('setup_app.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='SECRET', stderr='SECRET')):
            out = Path(directory) / 'new'
            with self.assertRaises(installer.SetupError) as error:
                setup_app.cloud_setup(out, mapping, lambda _: None)
            self.assertNotIn('SECRET', str(error.exception))
            self.assertFalse(out.exists())

    def test_missing_npm_does_not_provision(self):
        mapping = {key: 'sensor.test_' + key for key, *_ in installer.SENSORS}
        with tempfile.TemporaryDirectory() as directory, patch('setup_app.shutil.which', return_value=None):
            with self.assertRaises(installer.SetupError):
                setup_app.cloud_setup(Path(directory) / 'new', mapping, lambda _: None)


if __name__ == '__main__':
    unittest.main()
