from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from server.companion import authorization as auth


def scope_data():
    return {"owner": "user:1:agent:one", "operator_id": 1, "user_id": 1, "agent_id": "one",
            "persona_id": "mia", "device_id": "02:00:00:00:00:01", "client_id": "client",
            "binding_version": 1, "credential_version": 1,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "permissions": ["memory:read", "memory:write", "memory:manage"]}


class ScopeBoundaryTests(unittest.IsolatedAsyncioTestCase):
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
        self.assertIsNone(conn._mia_scope)
        self.assertIsNone(conn._mia_owner)

    async def test_revoked_output_stops_audio_and_does_not_repeat_authorization_notifications(self):
        conn = SimpleNamespace(read_config_from_api=True, session_id="fixture", client_abort=False,
                               websocket=SimpleNamespace(send=AsyncMock()), _mia_scope=auth._manager_scope(scope_data()),
                               _mia_authorization=SimpleNamespace(require=AsyncMock(side_effect=auth.PrivateAuthorizationRequired())))
        self.assertFalse(await auth.allow_output(conn))
        self.assertFalse(await auth.allow_output(conn))
        self.assertTrue(conn.client_abort)
        self.assertTrue(conn._mia_authorization_required)
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

    def test_incomplete_tls_material_fails_startup_instead_of_downgrading(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(auth.server_tls_context())
        for material in [{"MIA_TLS_CERT_FILE": "/missing/cert"}, {"MIA_TLS_KEY_FILE": "/missing/key"}]:
            with patch.dict("os.environ", material, clear=True), self.assertRaises(ValueError):
                auth.server_tls_context()


if __name__ == "__main__":
    unittest.main()
