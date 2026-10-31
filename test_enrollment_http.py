"""Real aiohttp -> Node Worker -> SQLite; HA UI/storage use framework doubles."""
import asyncio
from pathlib import Path
import subprocess
import types
import unittest
import aiohttp
from test_hacs import flow, api, fixture, const


class LoopbackSession:
    def __init__(self, session, origin): self.session, self.origin = session, origin
    def request(self, method, url, **kwargs):
        assert url.startswith(const.DEFAULT_RELAY + '/')
        return self.session.request(method, self.origin + url[len(const.DEFAULT_RELAY):], **kwargs)


class HttpSetupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = subprocess.Popen(['node', 'cloudflare/public-beta/enrollment-http-fixture.mjs'],
            cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        port = await asyncio.wait_for(asyncio.to_thread(self.server.stdout.readline), timeout=15)
        assert port.strip().isdigit()
        self.http = aiohttp.ClientSession()
        self.session = LoopbackSession(self.http, 'http://127.0.0.1:' + port.strip())

    async def asyncTearDown(self):
        await self.http.close()
        self.server.terminate()
        await asyncio.to_thread(self.server.wait, 10)
        self.server.stdout.close()

    def new_flow(self):
        mapping, states = fixture()
        subject = flow.SolarConfigFlow()
        subject.hass = types.SimpleNamespace(data={}, storage={}, session=self.session,
            states=types.SimpleNamespace(get=states.get), config=types.SimpleNamespace(time_zone='Europe/Berlin'))
        return subject, mapping

    async def enroll(self, subject, mapping):
        self.assertEqual((await subject.async_step_user({}))['step_id'], 'live')
        self.assertEqual((await subject.async_step_live({'power_w': mapping['power_w']}))['step_id'], 'energy')
        self.assertEqual((await subject.async_step_energy({}))['step_id'], 'consent')
        result = await subject.async_step_consent({'consent': True})
        self.assertEqual(result['type'], 'create_entry')
        return result['data']

    async def test_two_households_retry_upload_pairing_and_delete(self):
        first, mapping = self.new_flow()
        a = await self.enroll(first, mapping)
        # A second setup attempt with the persisted installation key recovers A.
        retry, _ = self.new_flow()
        retry.hass.storage = first.hass.storage
        self.assertEqual(await self.enroll(retry, mapping), a)
        second, _ = self.new_flow()
        b = await self.enroll(second, mapping)
        self.assertNotEqual(a['tenant_id'], b['tenant_id'])
        self.assertNotEqual(a['write_token'], b['write_token'])
        ra = api.Relay(self.session, a['relay_url'], a['write_token'])
        rb = api.Relay(self.session, b['relay_url'], b['write_token'])
        self.assertTrue((await ra.call('POST', '/v1/pv', {'power_w': 321, 'energy_date': '2026-10-31'}))['ok'])
        self.assertTrue((await rb.call('POST', '/v1/pv', {'power_w': 654, 'energy_date': '2026-10-31'}))['ok'])
        self.assertIn('pair_code', await ra.call('POST', '/v1/pair', {}))
        self.assertIn('pair_code', await rb.call('POST', '/v1/pair', {}))
        with self.assertRaises(api.RelayError):
            await ra.call('GET', '/v1/pv')  # A writer never becomes a reader.
        options = flow.SolarOptionsFlow(types.SimpleNamespace(data=a, options={}))
        options.hass = first.hass
        self.assertTrue((await options.async_step_erase({'confirm': True}))['data']['revoked'])
        with self.assertRaises(api.RelayError):
            await ra.call('POST', '/v1/pair', {})
        self.assertIn('pair_code', await rb.call('POST', '/v1/pair', {}))
        new = await self.enroll(first, mapping)
        self.assertNotEqual(a['tenant_id'], new['tenant_id'])
        self.assertNotEqual(a['write_token'], new['write_token'])


if __name__ == '__main__': unittest.main()
