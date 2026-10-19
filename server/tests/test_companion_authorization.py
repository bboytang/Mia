from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import asyncio
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from server.companion import authorization as auth


def scope_data():
    return {"owner": "user:1:agent:one", "operator_id": 1, "user_id": 1, "agent_id": "one",
            "persona_id": "mia", "device_id": "02:00:00:00:00:01", "client_id": "client",
            "binding_version": 1, "credential_version": 1,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "permissions": ["memory:read", "memory:write", "memory:manage"]}


class ScopeBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_transport_reuse_still_revalidates_each_request_and_closes_once(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        data = scope_data()
        session = SimpleNamespace(aclose=AsyncMock())
        request = AsyncMock(side_effect=[data, data, dict(data, credential_version=2)])
        factory = Mock(return_value=session)
        client = SimpleNamespace(config=config['manager-api'], _build_client=factory, _async_request=request)
        manager = SimpleNamespace(_get_instance=lambda: client)
        authorization = auth.PrivateAuthorization(config, connection_loop=asyncio.get_running_loop())
        with patch.dict(sys.modules, {'config.manage_api_client': SimpleNamespace(ManageApiClient=manager)}):
            scope = await authorization.restore(auth._manager_scope(data).snapshot())
            await authorization.require(scope, 'memory:read')
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await authorization.require(scope, 'memory:read')
            self.assertEqual(request.await_count, 3)
            self.assertEqual(factory.call_count, 1)
            self.assertTrue(all(call.args[0] is session for call in request.call_args_list))
            await auth.close_connection(SimpleNamespace(_youmi_authorization=authorization))
            await authorization.close()
            session.aclose.assert_awaited_once()
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await authorization.require(scope, 'memory:read')
            self.assertEqual(request.await_count, 3)

    async def test_connection_session_is_not_shared_with_another_event_loop(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        sessions = []

        class Session:
            closed = 0
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                await self.aclose()
            async def aclose(self):
                self.closed += 1

        def factory():
            session = Session()
            sessions.append(session)
            return session

        request = AsyncMock(return_value={"fixture": True})
        client = SimpleNamespace(config=config['manager-api'], _build_client=factory, _async_request=request)
        manager = SimpleNamespace(_get_instance=lambda: client)
        authorization = auth.PrivateAuthorization(config, connection_loop=asyncio.get_running_loop())
        with patch.dict(sys.modules, {'config.manage_api_client': SimpleNamespace(ManageApiClient=manager)}):
            await authorization._request('/config/proof', {})
            await asyncio.to_thread(lambda: asyncio.run(authorization._request('/config/proof', {})))
            await authorization._request('/config/proof', {})
            self.assertEqual(len(sessions), 2)
            self.assertEqual([session.closed for session in sessions], [0, 1])
            self.assertIs(request.call_args_list[0].args[0], request.call_args_list[2].args[0])
            self.assertIsNot(request.call_args_list[0].args[0], request.call_args_list[1].args[0])
            await authorization.close()
            self.assertEqual([session.closed for session in sessions], [1, 1])

    async def test_connection_transport_timeout_and_cancel_do_not_retry_or_leave_a_running_request(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled):
                started, finished = asyncio.Event(), asyncio.Event()
                session = SimpleNamespace(aclose=AsyncMock())

                async def waiting(*args, **kwargs):
                    started.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        finished.set()

                request = AsyncMock(side_effect=waiting)
                factory = Mock(return_value=session)
                client = SimpleNamespace(config=config['manager-api'], _build_client=factory, _async_request=request)
                manager = SimpleNamespace(_get_instance=lambda: client)
                authorization = auth.PrivateAuthorization(config, connection_loop=asyncio.get_running_loop())
                with patch.dict(sys.modules, {'config.manage_api_client': SimpleNamespace(ManageApiClient=manager)}):
                    task = asyncio.create_task(authorization._request('/config/proof', {}, timeout=0.05))
                    await started.wait()
                    if cancelled:
                        task.cancel()
                    with self.assertRaises(asyncio.CancelledError if cancelled else auth.PrivateAuthorizationRequired):
                        await task
                    self.assertTrue(finished.is_set())
                    request.assert_awaited_once()
                    request.side_effect = None
                    request.return_value = {"fixture": True}
                    self.assertEqual(await authorization._request('/config/proof', {}), {"fixture": True})
                    self.assertEqual(factory.call_count, 1)
                    await authorization.close()
                    session.aclose.assert_awaited_once()

    async def test_closing_connection_rejects_a_late_inflight_authorization_response(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        started, finish = asyncio.Event(), asyncio.Event()
        session = SimpleNamespace(aclose=AsyncMock())

        async def waiting(*args, **kwargs):
            started.set()
            await finish.wait()
            return scope_data()

        request = AsyncMock(side_effect=waiting)
        client = SimpleNamespace(config=config['manager-api'], _build_client=Mock(return_value=session),
                                 _async_request=request)
        manager = SimpleNamespace(_get_instance=lambda: client)
        authorization = auth.PrivateAuthorization(config, connection_loop=asyncio.get_running_loop())
        with patch.dict(sys.modules, {'config.manage_api_client': SimpleNamespace(ManageApiClient=manager)}):
            task = asyncio.create_task(authorization._request('/config/proof', {}))
            await started.wait()
            await authorization.close()
            finish.set()
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await task
            session.aclose.assert_awaited_once()
            request.assert_awaited_once()

    async def test_post_disconnect_title_revalidates_scope_without_reopening_connection_transport(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        data = scope_data()
        authorization = auth.PrivateAuthorization(config, connection_loop=asyncio.get_running_loop())
        await authorization.close()
        conn = SimpleNamespace(config=config, _youmi_scope=auth._manager_scope(data),
                               _youmi_authorization=authorization, session_id='session-one')
        with patch.object(auth.PrivateAuthorization, '_request', new_callable=AsyncMock,
                          side_effect=[data, True]) as request:
            self.assertTrue(await auth.save_chat_title(conn))
            self.assertEqual(request.await_count, 2)
            self.assertEqual(request.call_args.args, ('/agent/chat-title/session-one/generate', conn._youmi_scope.snapshot()))
        with patch.object(auth.PrivateAuthorization, '_request', new_callable=AsyncMock,
                          return_value=dict(data, credential_version=2)) as request:
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await auth.save_chat_title(conn)
            request.assert_awaited_once()
        self.assertTrue(authorization._closed)
        self.assertIsNone(authorization._session)

    async def test_both_manager_client_signatures_use_one_request_and_close_owned_session(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        body = {"fixture": "trusted"}
        result = scope_data()
        session = object()
        closed = []

        @asynccontextmanager
        async def build_client():
            try:
                yield session
            finally:
                closed.append(True)

        for owned in (False, True):
            with self.subTest(owned_session=owned):
                request = AsyncMock(return_value=result)
                client = SimpleNamespace(config=config["manager-api"], _async_request=request)
                if owned:
                    client._build_client = build_client
                manager = SimpleNamespace(_get_instance=lambda: client)
                with patch.dict(sys.modules, {"config.manage_api_client": SimpleNamespace(ManageApiClient=manager)}):
                    self.assertEqual(await auth.PrivateAuthorization(config)._request("/config/proof", body), result)
                args = (session, "POST", "/config/proof") if owned else ("POST", "/config/proof")
                request.assert_awaited_once_with(*args, json=body, timeout=3)
        self.assertEqual(closed, [True])

    async def test_owned_manager_session_closes_on_denial_timeout_and_cancellation_without_retry(self):
        config = {"manager-api": {"url": "https://manager.example/xiaozhi"}}
        for failure in ("denied", "timeout", "cancelled"):
            with self.subTest(failure=failure):
                started, closed = asyncio.Event(), []

                @asynccontextmanager
                async def build_client():
                    try:
                        yield object()
                    finally:
                        closed.append(True)

                async def send(*args, **kwargs):
                    started.set()
                    if failure == "denied":
                        raise ValueError("private response must not escape")
                    await asyncio.Event().wait()

                request = AsyncMock(side_effect=send)
                client = SimpleNamespace(config=config["manager-api"], _build_client=build_client,
                                         _async_request=request)
                manager = SimpleNamespace(_get_instance=lambda: client)
                with patch.dict(sys.modules, {"config.manage_api_client": SimpleNamespace(ManageApiClient=manager)}):
                    task = asyncio.create_task(auth.PrivateAuthorization(config)._request("/config/proof", {}, timeout=0.05))
                    await started.wait()
                    if failure == "cancelled":
                        task.cancel()
                    with self.assertRaises(asyncio.CancelledError if failure == "cancelled" else auth.PrivateAuthorizationRequired):
                        await task
                request.assert_awaited_once()
                self.assertEqual(closed, [True])

    async def test_rejects_malformed_proof_and_expired_permission_before_any_request(self):
        valid = scope_data()
        self.assertEqual(auth._manager_scope(dict(valid, binding_version=0)).binding_version, 0)
        serialized = dict(valid, **{key: str(valid[key]) for key in (
            "operator_id", "user_id", "binding_version", "credential_version")})
        self.assertEqual(auth._manager_scope(serialized), auth._manager_scope(valid))
        for key, invalid in [("owner", "user:2:agent:one"), ("operator_id", True),
                             ("binding_version", 0.5), ("credential_version", 0),
                             ("binding_version", "0.5"), ("binding_version", "-1"),
                             ("operator_id", "9223372036854775808"), ("user_id", "01"),
                             ("persona_id", "other"), ("permissions", ["root"]),
                             ("expires_at", "2020-01-01T00:00:00Z")]:
            with self.subTest(key=key), self.assertRaises(auth.PrivateAuthorizationRequired):
                auth._manager_scope(dict(valid, **{key: invalid}))
        authorization = auth.PrivateAuthorization({})
        with patch.object(authorization, "_request", new_callable=AsyncMock) as request:
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await authorization.require(auth._manager_scope(valid), "root")
            request.assert_not_awaited()

    async def test_manager_config_disagreement_cannot_attach_scope_or_load_correct_words(self):
        data = scope_data()
        authorization = auth.PrivateAuthorization({})
        with patch.object(authorization, "_request", new_callable=AsyncMock,
                          side_effect=[data, {"mia_owner": "user:2:agent:one", "mia_scope": data}]) as request:
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await authorization.private_config(data["device_id"], "client", "a" * 43, {})
            self.assertEqual(request.await_count, 2)

    async def test_transport_header_is_consumed_and_rejected_before_plaintext_manager_call(self):
        conn = SimpleNamespace(config={}, headers={"mia-private-credential": "a" * 43},
                               websocket=SimpleNamespace(transport=None))
        with patch.object(auth.PrivateAuthorization, "private_config", new_callable=AsyncMock) as request:
            with self.assertRaises(auth.PrivateAuthorizationRequired):
                await auth.load_private_config(conn)
            request.assert_not_awaited()
        self.assertNotIn("mia-private-credential", conn.headers)
        self.assertIsNone(conn._youmi_scope)
        self.assertIsNone(conn._youmi_owner)

    async def test_revoked_output_stops_audio_and_does_not_repeat_authorization_notifications(self):
        conn = SimpleNamespace(read_config_from_api=True, session_id="fixture", client_abort=False,
                               websocket=SimpleNamespace(send=AsyncMock()), _youmi_scope=auth._manager_scope(scope_data()),
                               _youmi_authorization=SimpleNamespace(require=AsyncMock(side_effect=auth.PrivateAuthorizationRequired())))
        self.assertFalse(await auth.allow_output(conn))
        self.assertFalse(await auth.allow_output(conn))
        self.assertTrue(conn.client_abort)
        self.assertTrue(conn._youmi_authorization_required)
        conn.websocket.send.assert_awaited_once()
        self.assertEqual(json.loads(conn.websocket.send.call_args.args[0])["message"], "请用智控台授权码完成授权")
        conn.func_handler = SimpleNamespace(handle_llm_function_call=AsyncMock())
        with self.assertRaises(auth.PrivateAuthorizationRequired):
            await auth.execute_tool(conn, {"name": "private_tool"})
        conn.func_handler.handle_llm_function_call.assert_not_awaited()
        conn.intent = SimpleNamespace(replyResult=AsyncMock())
        with self.assertRaises(auth.PrivateAuthorizationRequired):
            await auth.intent_reply(conn, "private context", "query")
        conn.intent.replyResult.assert_not_awaited()

    async def test_report_preserves_payload_and_only_sends_verified_snapshot(self):
        scope = auth._manager_scope(scope_data())
        authorization = SimpleNamespace(require=AsyncMock(return_value=scope), _request=AsyncMock(return_value=True))
        conn = SimpleNamespace(read_config_from_api=True, _youmi_scope=scope,
                               _youmi_authorization=authorization, session_id="session-one")
        self.assertTrue(await auth.report_chat(conn, scope.device_id, conn.session_id, 1, "合成测试", b"audio", 123))
        endpoint, body = authorization._request.call_args.args
        self.assertEqual(endpoint, "/agent/chat-history/report")
        self.assertEqual(body, {"macAddress": scope.device_id, "sessionId": "session-one", "chatType": 1,
                               "content": "合成测试", "audioBase64": "YXVkaW8=", "reportTime": 123,
                               "miaScope": scope.snapshot()})
        authorization._request.reset_mock()
        with self.assertRaises(auth.PrivateAuthorizationRequired):
            await auth.report_chat(conn, "foreign-device", conn.session_id, 1, "test", None, 123)
        authorization._request.assert_not_awaited()
        authorization.require.side_effect = auth.PrivateAuthorizationRequired()
        with self.assertRaises(auth.PrivateAuthorizationRequired):
            await auth.report_chat(conn, scope.device_id, conn.session_id, 1, "test", None, 123)
        with self.assertRaises(auth.PrivateAuthorizationRequired):
            await auth.save_chat_title(conn)
        authorization._request.assert_not_awaited()

    def test_incomplete_tls_material_fails_startup_instead_of_downgrading(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(auth.server_tls_context())
        for material in [{"MIA_TLS_CERT_FILE": "/missing/cert"}, {"MIA_TLS_KEY_FILE": "/missing/key"}]:
            with patch.dict("os.environ", material, clear=True), self.assertRaises(ValueError):
                auth.server_tls_context()


if __name__ == "__main__":
    unittest.main()
