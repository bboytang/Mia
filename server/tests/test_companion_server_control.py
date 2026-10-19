import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from server.companion.authorization import route_server_control


class ServerControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_console_needs_tls_and_server_secret_but_no_private_device_scope(self):
        handler = AsyncMock()
        module = SimpleNamespace(ServerTextMessageHandler=lambda: SimpleNamespace(handle=handler))
        websocket = SimpleNamespace(send=AsyncMock(), transport=SimpleNamespace(get_extra_info=lambda _: object()))
        conn = SimpleNamespace(config={'manager-api': {'secret': 'server-secret'}}, websocket=websocket,
                               read_config_from_api=True, _youmi_authorization_required=True)
        def command(secret='server-secret', action='update_config'):
            return json.dumps({'type': 'server', 'action': action, 'content': {'secret': secret}})
        with patch.dict(sys.modules, {'core.handle.textHandler.serverMessageHandler': module}):
            self.assertTrue(await route_server_control(conn, command()))
            self.assertTrue(await route_server_control(conn, command(action='restart')))
            self.assertEqual(handler.await_count, 2)
            for invalid in [command('bad'), command('秘密'), command(action='chat'),
                            json.dumps({'type': 'server', 'action': 'restart', 'content': None})]:
                self.assertTrue(await route_server_control(conn, invalid))
            websocket.transport = None
            self.assertTrue(await route_server_control(conn, command()))
            self.assertEqual(handler.await_count, 2)
        for ordinary in ['{"type":"hello"}', '{', b'voice', 'x' * 16385]:
            self.assertFalse(await route_server_control(conn, ordinary))
