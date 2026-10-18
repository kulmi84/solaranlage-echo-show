"""Offline tests of conversions, transport, upload scheduling and flow transitions.

HA framework edges are explicit test doubles; this is not an HA runtime test.
"""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

COMPONENT = Path(__file__).parent / 'custom_components/solaranlage_echo'
package = types.ModuleType('_solar_test'); package.__path__ = [str(COMPONENT)]
sys.modules['_solar_test'] = package


def load(name, file=None):
    spec = importlib.util.spec_from_file_location('_solar_test.' + name, COMPONENT / (file or name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


const = load('const'); payload = load('payload'); api = load('api')


class FrameworkFlow:
    def __init_subclass__(cls, **kwargs): pass
    def async_show_form(self, **kwargs): return {'type': 'form', **kwargs}
    def async_show_menu(self, **kwargs): return {'type': 'menu', **kwargs}
    def async_create_entry(self, **kwargs): return {'type': 'create_entry', **kwargs}
    def async_abort(self, **kwargs): return {'type': 'abort', **kwargs}
    async def async_set_unique_id(self, value): self.unique = value
    def _abort_if_unique_id_configured(self): pass


class Coordinator:
    def __init__(self, hass, logger, **kwargs): self.hass = hass
    def async_set_updated_data(self, data): self.data = data


fake_entries = types.SimpleNamespace(ConfigFlow=FrameworkFlow, OptionsFlow=FrameworkFlow)
fake_ha = types.SimpleNamespace(config_entries=fake_entries)
fake_helpers = {
    'homeassistant': fake_ha, 'homeassistant.config_entries': fake_entries,
    'homeassistant.core': types.SimpleNamespace(callback=lambda f: f),
    'homeassistant.const': types.SimpleNamespace(Platform=types.SimpleNamespace(SENSOR='sensor'), EVENT_HOMEASSISTANT_STARTED='start'),
    'homeassistant.helpers.aiohttp_client': types.SimpleNamespace(async_get_clientsession=lambda hass: hass.session),
    'homeassistant.helpers.selector': types.SimpleNamespace(EntitySelector=lambda config: str, EntitySelectorConfig=lambda **kwargs: kwargs, TextSelector=lambda config: str, TextSelectorConfig=lambda **kwargs: kwargs),
    'homeassistant.helpers.event': types.SimpleNamespace(async_track_time_interval=lambda *args: lambda: None),
    'homeassistant.helpers.update_coordinator': types.SimpleNamespace(DataUpdateCoordinator=Coordinator),
    'homeassistant.util': types.SimpleNamespace(dt=types.SimpleNamespace(now=lambda: datetime(2026, 10, 18, 12, tzinfo=timezone.utc), utcnow=lambda: datetime.now(timezone.utc))),
}
with patch.dict(sys.modules, fake_helpers):
    flow = load('config_flow')
    upload = load('uploader', '__init__.py')


def fixture():
    mapping = {key: 'sensor.' + key for key in const.FIELDS}
    states = {entity: types.SimpleNamespace(state='5', attributes={
        'unit_of_measurement': {'power': 'W', 'percent': '%', 'energy': 'kWh'}[const.FIELDS[key][1]],
        'state_class': 'total_increasing'}) for key, entity in mapping.items()}
    return mapping, states


class PayloadTests(unittest.TestCase):
    def test_power_units_and_unknowns_are_not_zero(self):
        mapping, states = fixture()
        states[mapping['power_w']].attributes['unit_of_measurement'] = 'kW'
        states[mapping['battery_soc']].state = '101'
        states[mapping['bkw_w']].state = 'unavailable'
        result = payload.live_values(mapping, states.get)
        self.assertEqual(result['power_w'], 5000)
        self.assertIsNone(result['battery_soc']); self.assertIsNone(result['bkw_w'])
        self.assertNotIn('energy_pv', result)

    def test_energy_balance_requires_all_sources_and_handles_zero(self):
        mapping, _ = fixture()
        stats = {'statistics': {mapping[key]: [{'change': 0}] for key in const.ENERGY_KEYS}}
        result = payload.energy_values(mapping, stats, 'month')
        self.assertEqual(result['month_home_kwh'], 0)
        del stats['statistics'][mapping['energy_bkw']]
        result = payload.energy_values(mapping, stats, 'year')
        self.assertIsNone(result['year_pv_kwh']); self.assertIsNone(result['year_home_kwh'])
        self.assertEqual(result['year_grid_import_kwh'], 0)

    def test_urls_do_not_accept_credentials_http_or_paths(self):
        for url in ['http://relay.test', 'https://u:p@relay.test', 'https://relay.test/pv', 'https://relay.test?token=x']:
            with self.assertRaises(ValueError): api.relay_url(url)


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mapping, self.states = fixture()
        self.hass = types.SimpleNamespace(states=types.SimpleNamespace(get=self.states.get), session=object(), config=types.SimpleNamespace(time_zone='Europe/Berlin'))

    async def test_enrollment_only_after_sensor_validation_and_explicit_consent(self):
        subject = flow.SolarConfigFlow(); subject.hass = self.hass
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock) as call:
            call.return_value = {'ok': True}
            first = await subject.async_step_user({'relay_url': 'https://relay.test', 'invite': 'invite'})
            self.assertEqual(first['step_id'], 'live')
            self.assertEqual(call.call_args.args[1], '/v1/health')
            live = {k: v for k, v in self.mapping.items() if k not in const.ENERGY_KEYS}
            self.assertEqual((await subject.async_step_live(live))['step_id'], 'energy')
            energy = {k: self.mapping[k] for k in const.ENERGY_KEYS}
            self.assertEqual((await subject.async_step_energy(energy))['step_id'], 'consent')
            self.assertEqual((await subject.async_step_consent({'consent': False}))['type'], 'form')
            self.assertEqual(call.await_count, 1)
            call.return_value = {'tenant_id': 'tenant', 'write_token': 'a' * 64}
            done = await subject.async_step_consent({'consent': True})
            self.assertEqual(done['type'], 'create_entry')
            self.assertNotIn('invite', done['data']); self.assertNotIn('ha_token', done['data'])
            self.assertEqual(done['data']['sensors'], self.mapping)

    async def test_bad_units_and_duplicate_energy_are_rejected(self):
        self.states[self.mapping['power_w']].attributes['unit_of_measurement'] = 'kWh'
        subject = flow.SolarConfigFlow(); subject.hass = self.hass
        result = await subject.async_step_live({'power_w': self.mapping['power_w']})
        self.assertEqual(result['errors']['power_w'], 'invalid_sensor')
        self.assertIn('duplicate_energy', flow.validate_sensors(self.hass, {'energy_pv': self.mapping['energy_pv'], 'energy_bkw': self.mapping['energy_pv']}).values())

    async def test_connection_failures_do_not_create_configuration(self):
        subject = flow.SolarConfigFlow(); subject.hass = self.hass
        with patch.object(flow.Relay, 'call', side_effect=api.RelayError('cannot_connect')):
            result = await subject.async_step_user({'relay_url': 'https://relay.test', 'invite': 'private'})
        self.assertEqual(result['errors']['base'], 'cannot_connect')
        self.assertNotIn('private', str(result))


class UploadTests(unittest.IsolatedAsyncioTestCase):
    def create(self):
        mapping, states = fixture()
        stats = {'statistics': {mapping[key]: [{'change': 5}] for key in const.ENERGY_KEYS}}
        hass = types.SimpleNamespace(session=object(), states=types.SimpleNamespace(get=states.get), services=types.SimpleNamespace(async_call=AsyncMock(return_value=stats)))
        entry = types.SimpleNamespace(data={'relay_url': 'https://relay.test', 'write_token': 'a' * 64, 'sensors': mapping}, options={})
        instance = upload.SolarUploader(hass, entry); instance.relay.call = AsyncMock(return_value={'ok': True})
        return instance, states

    async def test_minutes_and_history_bucket_and_only_allowlisted_data(self):
        instance, _ = self.create()
        await instance.upload(); await instance.upload()
        self.assertEqual(instance.relay.call.await_count, 3)
        first = instance.relay.call.call_args_list[0].args[2]
        self.assertEqual(first['power_w'], 5)
        self.assertNotIn('sensor.', json.dumps(first))
        self.assertEqual(instance.relay.call.call_args_list[1].args[2]['month_pv_kwh'], 10)
        self.assertEqual(instance.data['status'], 'online')
        instance.closed = True
        await instance.upload()
        self.assertEqual(instance.relay.call.await_count, 3)

    async def test_recorder_failure_preserves_live_without_fabricating_energy(self):
        instance, _ = self.create()
        instance.hass.services.async_call.side_effect = RuntimeError('recorder unavailable')
        await instance.upload()
        first = instance.relay.call.call_args_list[0].args[2]
        self.assertIsNone(first['today_pv_kwh'])
        self.assertIsNone(first['today_home_kwh'])
        self.assertIsNone(instance.last_history)
        self.assertEqual(instance.data['history_status'], 'statistics_missing')

    async def test_missing_primary_and_revoked_entry_send_nothing(self):
        instance, states = self.create()
        states['sensor.power_w'].state = 'unavailable'
        await instance.upload()
        instance.relay.call.assert_not_awaited()
        self.assertEqual(instance.data['status'], 'sensor_missing')
        instance.entry.options['revoked'] = True
        await instance.upload(); instance.relay.call.assert_not_awaited()


class AlexaAccountTests(unittest.TestCase):
    def test_public_mode_requires_link_and_uses_only_request_access_token(self):
        import beta_live_lambda
        event = {'request': {'type': 'LaunchRequest'}, 'context': {'System': {'user': {}, 'device': {'supportedInterfaces': {}}}}}
        config = json.dumps({'mode': 'public_beta', 'url': 'https://relay.test/v1/pv', 'read_token': 'must-not-use'})
        with patch('pathlib.Path.read_text', return_value=config), patch('beta_live_lambda.read_pv') as read:
            result = beta_live_lambda.lambda_handler(event, None)
            self.assertEqual(result['response']['card']['type'], 'LinkAccount'); read.assert_not_called()
            event['context']['System']['user']['accessToken'] = 'household-A'
            read.return_value = {'metrics': {}, 'valueText': '0', 'stale': False, 'statusText': ''}
            beta_live_lambda.lambda_handler(event, None)
            read.assert_called_once_with('https://relay.test/v1/pv', 'household-A')


if __name__ == '__main__': unittest.main()
