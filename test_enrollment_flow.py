"""Registration flow and HTTP contract; framework edges use explicit doubles."""
import asyncio
import json
import types
import unittest
from unittest.mock import AsyncMock, patch
from test_hacs import flow, api, fixture, const
from test_hacs import MemoryStore
from test_hacs import COMPONENT


class EnrollmentFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mapping, states = fixture()
        self.hass = types.SimpleNamespace(data={}, storage={}, session=object(),
            states=types.SimpleNamespace(get=states.get), config=types.SimpleNamespace(time_zone='Europe/Berlin'))

    def subject(self):
        subject = flow.SolarConfigFlow()
        subject.hass = self.hass
        return subject

    async def start(self, subject, call):
        call.side_effect = [{'ok': True, 'api': 1}, {'mode': 'automatic'}]
        result = await subject.async_step_user({})
        self.assertEqual(result['step_id'], 'live')
        call.side_effect = None

    async def test_no_account_or_key_before_consent_and_no_key_in_config_entry(self):
        subject = self.subject()
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock) as call:
            await self.start(subject, call)
            self.assertEqual((await subject.async_step_consent({'consent': False}))['errors']['base'], 'consent_required')
            self.assertEqual(self.hass.storage, {})
            self.assertEqual(call.await_count, 2)
            call.return_value = {'tenant_id': 'household', 'write_token': 'a' * 64}
            result = await subject.async_step_consent({'consent': True})
            method, path, payload = call.call_args.args
            self.assertEqual((method, path), ('POST', '/v2/enroll'))
            self.assertEqual(set(payload), {'installation_key', 'timezone'})
            self.assertEqual(len(payload['installation_key']), 64)
            self.assertEqual(set(result['data']), {'relay_url', 'write_token', 'tenant_id', 'sensors'})
            self.assertNotIn(payload['installation_key'], json.dumps(result))

    async def test_lost_reply_and_restart_reuse_durable_key(self):
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock) as call:
            first = self.subject()
            await self.start(first, call)
            call.side_effect = api.RelayError('registration_unavailable')
            self.assertEqual((await first.async_step_consent({'consent': True}))['type'], 'form')
            key = call.call_args.args[2]['installation_key']
            self.hass.data = {}  # Simulate restart; persisted storage survives.
            second = self.subject()
            await self.start(second, call)
            call.return_value = {'tenant_id': 'same-household', 'write_token': 'a' * 64}
            self.assertEqual((await second.async_step_consent({'consent': True}))['type'], 'create_entry')
            self.assertEqual(call.call_args.args[2]['installation_key'], key)

    async def test_only_missing_capability_route_falls_back(self):
        for capability in ({'mode': 'invitation'}, api.RelayError('enrollment_unsupported')):
            with patch.object(flow.Relay, 'call', new_callable=AsyncMock,
                              side_effect=[{'ok': True}, capability]) as call:
                subject = self.subject()
                self.assertEqual((await subject.async_step_user({}))['step_id'], 'invite')
                self.assertEqual((await subject.async_step_invite({'invite': ' code '}))['step_id'], 'live')
                call.side_effect = None
                call.return_value = {'tenant_id': 'old', 'write_token': 'b' * 64}
                await subject.async_step_consent({'consent': True})
                self.assertEqual(call.call_args.args[1:], ('/v1/enroll', {'invite': 'code', 'timezone': 'Europe/Berlin'}))
        with patch.object(flow.Relay, 'call', side_effect=[{'ok': True}, api.RelayError('cannot_connect')]):
            result = await self.subject().async_step_user({})
            self.assertEqual(result['errors']['base'], 'cannot_connect')

    async def test_revoked_key_requires_new_explicit_consent(self):
        subject = self.subject()
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock) as call:
            await self.start(subject, call)
            call.side_effect = api.RelayError('registration_revoked')
            result = await subject.async_step_consent({'consent': True})
            old_key = call.call_args.args[2]['installation_key']
            self.assertEqual(result['errors']['base'], 'registration_revoked')
            self.assertEqual(call.await_count, 3)  # No automatic second registration.
            self.assertFalse(self.hass.storage)
            call.side_effect = None
            call.return_value = {'tenant_id': 'new', 'write_token': 'b' * 64}
            await subject.async_step_consent({'consent': True})
            self.assertNotEqual(call.call_args.args[2]['installation_key'], old_key)

    async def test_private_keys_are_separate_by_server_and_deleted_selectively(self):
        first, duplicate = await asyncio.gather(flow.installation_key(self.hass, 'https://a.test'),
                                               flow.installation_key(self.hass, 'https://a.test'))
        other = await flow.installation_key(self.hass, 'https://b.test')
        self.assertEqual(first, duplicate)
        self.assertNotEqual(first, other)
        await flow.forget_installation(self.hass, 'https://a.test')
        self.assertEqual(await flow.installation_key(self.hass, 'https://b.test'), other)
        self.assertNotEqual(await flow.installation_key(self.hass, 'https://a.test'), first)

    async def test_storage_failure_prevents_registration(self):
        subject = self.subject()
        subject._connection = {'mode': 'automatic', 'relay_url': const.DEFAULT_RELAY}
        with patch.object(flow, 'installation_key', side_effect=OSError('disk full')), patch.object(flow.Relay, 'call') as call:
            self.assertEqual((await subject.async_step_consent({'consent': True}))['errors']['base'], 'cannot_connect')
            call.assert_not_called()

    async def test_silently_failed_storage_write_prevents_account_creation(self):
        subject = self.subject()
        subject._connection = {'mode': 'automatic', 'relay_url': const.DEFAULT_RELAY}
        with patch.object(MemoryStore, 'async_save', new_callable=AsyncMock), patch.object(flow.Relay, 'call') as call:
            result = await subject.async_step_consent({'consent': True})
            self.assertEqual(result['errors']['base'], 'cannot_connect')
            call.assert_not_called()

    async def test_custom_server_validation_preserves_server_form(self):
        result = await self.subject().async_step_server({'relay_url': 'http://invalid.test'})
        self.assertEqual(result['step_id'], 'server')
        self.assertEqual(result['errors']['base'], 'invalid_url')

    async def test_limits_display_safe_errors_without_clearing_retry_key(self):
        subject = self.subject()
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock) as call:
            await self.start(subject, call)
            for error in ('registration_full', 'registration_rate_limited'):
                call.side_effect = api.RelayError(error)
                result = await subject.async_step_consent({'consent': True})
                self.assertEqual(result['errors']['base'], error)
                key = call.call_args.args[2]['installation_key']
                self.assertEqual(await flow.installation_key(self.hass, const.DEFAULT_RELAY), key)

    async def test_existing_options_delete_only_their_account_and_local_key(self):
        base = const.DEFAULT_RELAY
        await flow.installation_key(self.hass, base)
        other = await flow.installation_key(self.hass, 'https://other.test')
        entry = types.SimpleNamespace(data={'relay_url': base, 'write_token': 'a' * 64}, options={})
        subject = flow.SolarOptionsFlow(entry)
        subject.hass = self.hass
        with patch.object(flow.Relay, 'call', new_callable=AsyncMock, return_value={'ok': True}) as call:
            result = await subject.async_step_erase({'confirm': True})
            call.assert_awaited_once_with('DELETE', '/v1/account')
            self.assertTrue(result['data']['revoked'])
        self.assertEqual(await flow.installation_key(self.hass, 'https://other.test'), other)
        saved = next(iter(self.hass.storage.values()))['installations']
        self.assertNotIn(base, saved)

    async def test_new_forms_and_errors_have_both_translations(self):
        for filename in ('strings.json', 'translations/de.json'):
            content = json.loads((COMPONENT / filename).read_text(encoding='utf-8'))['config']
            self.assertEqual(set(content['step']['user']['data']), {'custom_server'})
            self.assertEqual(set(content['step']['server']['data']), {'relay_url'})
            self.assertEqual(set(content['step']['invite']['data']), {'invite'})
            for code in ('registration_full', 'registration_rate_limited', 'registration_revoked',
                         'registration_not_ready', 'registration_invalid', 'registration_ip_unavailable',
                         'registration_unavailable'):
                self.assertTrue(content['error'][code])


class Response:
    def __init__(self, status, body):
        self.status, self.body, self.content = status, body, self
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def iter_chunked(self, size):
        for index in range(0, len(self.body), size): yield self.body[index:index + size]


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, status, body, path='/v2/enroll'):
        session = types.SimpleNamespace(request=unittest.mock.Mock(return_value=Response(status, body)))
        try:
            return await api.Relay(session, 'https://relay.test').call('POST', path, {})
        finally:
            self.assertFalse(session.request.call_args.kwargs['allow_redirects'])

    async def test_registration_errors_are_allowlisted_and_status_matched(self):
        cases = [(429, b'{"error":"registration_rate_limited"}', 'registration_rate_limited'),
                 (503, b'{"error":"registration_full"}', 'registration_full'),
                 (410, b'{"error":"registration_revoked"}', 'registration_revoked'),
                 (500, b'{"error":"secret-private-string"}', 'registration_unavailable'),
                 (400, b'{"error":"registration_full"}', 'registration_unavailable'),
                 (503, b'not json', 'registration_unavailable')]
        for status, body, expected in cases:
            with self.assertRaisesRegex(api.RelayError, '^' + expected + '$'):
                await self.request(status, body)

    async def test_capability_404_only_and_old_errors_preserved(self):
        for path, status, expected in [('/v2/enrollment', 404, 'enrollment_unsupported'),
                                       ('/v1/enroll', 403, 'invalid_invite'),
                                       ('/v1/enroll', 409, 'beta_full'),
                                       ('/v2/enrollment', 500, 'cannot_connect')]:
            with self.assertRaisesRegex(api.RelayError, '^' + expected + '$'):
                await self.request(status, b'{}', path)

    async def test_bounded_json_object_required(self):
        for body in (b'x' * 8193, b'[]', b'null', b'invalid'):
            with self.assertRaisesRegex(api.RelayError, '^cannot_connect$'):
                await self.request(200, body)
        self.assertEqual(await self.request(201, b'{"tenant_id":"new"}'), {'tenant_id': 'new'})


if __name__ == '__main__': unittest.main()
