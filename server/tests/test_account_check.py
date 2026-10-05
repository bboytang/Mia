import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from aiohttp import web
from websockets.asyncio.server import serve

from server.account_http import create_app
from server.account_store import AccountStore
from server.deploy.check_accounts import check
from server.tests.test_xiaozhi_gateway import FakeProvider
from server.xiaozhi_gateway import MiaGateway


class AccountCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_deployed_check_revokes_before_cloud_and_cleans_only_its_user(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "accounts.sqlite3"
            store = AccountStore(database)
            existing = await store.register("existing_friend", "a long existing password")
            provider = FakeProvider()
            gateway = MiaGateway("maintenance-test", lambda: provider, accounts=store)
            runner = web.AppRunner(create_app(store), access_log=None)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            try:
                async with serve(gateway.handle_client, "127.0.0.1", 0) as sockets:
                    origin = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
                    endpoint = f"ws://127.0.0.1:{sockets.sockets[0].getsockname()[1]}"
                    output = io.StringIO()
                    with redirect_stdout(output):
                        await check(origin, endpoint, database)
                    self.assertIn("账号注册、登录、握手、退出及撤销后拒绝新回合：通过", output.getvalue())
                    self.assertNotIn(existing["token"], output.getvalue())
                    self.assertIsNone(provider.recording)
                    self.assertIsNotNone(store.authenticate(existing["token"]))
                    self.assertEqual(store.db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            finally:
                await runner.cleanup()
                await store.close()
