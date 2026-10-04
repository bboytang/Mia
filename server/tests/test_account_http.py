import asyncio
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer, make_mocked_request

from server.account_store import AccountStore, password_digest
from server.account_http import client_ip, create_app
from server.tests.test_accounts import PASSWORD


class AccountHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.temp.name) / "accounts.sqlite3")
        self.client = TestClient(TestServer(create_app(self.store), handler_cancellation=True))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        await self.store.close()
        self.temp.cleanup()

    async def post(self, route, username="friends", password=PASSWORD, **kwargs):
        return await self.client.post("/api/auth/" + route,
                                      json={"username": username, "password": password}, **kwargs)

    async def test_register_login_logout_and_no_store(self):
        registered = await self.post("register")
        self.assertEqual(registered.status, 201)
        self.assertEqual(registered.headers.get("Cache-Control"), "no-store")
        original = await registered.json()
        self.assertEqual(set(original), {"username", "token", "expires_at"})
        logged_in = await self.post("login")
        self.assertEqual(logged_in.status, 200)
        credential = await logged_in.json()
        self.assertIsNotNone(self.store.authenticate(credential["token"]))
        for _ in range(2):
            result = await self.client.post("/api/auth/logout", headers={
                "Authorization": "Bearer " + credential["token"]})
            self.assertEqual(result.status, 204)
            self.assertEqual(result.headers.get("Cache-Control"), "no-store")
        self.assertIsNone(self.store.authenticate(credential["token"]))
        self.assertIsNotNone(self.store.authenticate(original["token"]))

    async def test_json_limits_invalid_inputs_and_duplicate(self):
        cases = [({"data": "not-json", "headers": {"Content-Type": "application/json"}}, 400),
                 ({"data": "plain"}, 415), ({"json": []}, 400),
                 ({"json": {"username": "good", "password": 17}}, 400),
                 ({"data": "x" * 4097, "headers": {"Content-Type": "application/json"}}, 413)]
        for kwargs, status in cases:
            with self.subTest(status=status, body_type=type(kwargs.get("json")).__name__):
                result = await self.client.post("/api/auth/register", **kwargs)
                self.assertEqual(result.status, status)
                self.assertEqual(result.headers.get("Cache-Control"), "no-store")
                self.assertNotIn("traceback", (await result.text()).lower())
        self.assertEqual((await self.post("register")).status, 201)
        self.assertEqual((await self.post("register", "ＦＲＩＥＮＤＳ")).status, 409)
        body = json.dumps({"username": "body_limit", "password": PASSWORD}).ljust(4096)
        exact = await self.client.post("/api/auth/register", data=body,
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(exact.status, 201)

    async def test_cancelled_http_hash_and_overload_keep_actual_slots(self):
        release = threading.Event()
        started = threading.Event()
        lock = threading.Lock()
        count = [0]

        def blocked(password, salt):
            with lock:
                count[0] += 1
                if count[0] == 2:
                    started.set()
            release.wait(timeout=5)
            return password_digest(password, salt)

        with patch("server.account_store.password_digest", blocked):
            first = asyncio.create_task(self.post("register", "cancelled_http"))
            second = asyncio.create_task(self.post("register", "running_http"))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                first.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await first
                rejected = await self.post("register", "third_http")
                self.assertEqual(rejected.status, 429)
            finally:
                release.set()
                self.assertEqual((await second).status, 201)
        self.assertEqual(self.store.db.execute(
            "SELECT count(*) FROM users WHERE username='cancelled_http'").fetchone()[0], 0)

    async def test_wrong_password_and_unknown_user_are_indistinguishable(self):
        await self.post("register")
        bodies = []
        for username in ["friends", "unknown"]:
            result = await self.post("login", username, PASSWORD + "wrong")
            self.assertEqual(result.status, 401)
            bodies.append(await result.json())
        self.assertEqual(bodies[0], bodies[1])

    async def test_username_rate_limit_precedes_hash_and_resets(self):
        now = [0.0]
        # Clock is owned by limiter, without replacing store/hash behavior.
        await self.client.close()
        self.client = TestClient(TestServer(create_app(self.store, clock=lambda: now[0])))
        await self.client.start_server()
        for i in range(10):
            result = await self.post("login", "ＲＡＴＥＤ" if i % 2 else "rated")
            self.assertEqual(result.status, 401)
        with patch("server.account_store.password_digest", side_effect=AssertionError("hash must not run")):
            rejected = await self.post("login", "rated")
            self.assertEqual(rejected.status, 429)
            self.assertEqual(rejected.headers.get("Retry-After"), "60")
        now[0] = 60
        self.assertEqual((await self.post("login", "rated")).status, 401)

    async def test_ip_limit_applies_to_many_usernames(self):
        for i in range(20):
            self.assertEqual((await self.post("login", "unknown" + str(i))).status, 401)
        rejected = await self.post("register", "other_friend")
        self.assertEqual(rejected.status, 429)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM users").fetchone()[0], 0)

    async def test_internal_error_does_not_echo_secret(self):
        secret = "not-a-real-secret-for-error-test"
        with patch.object(self.store, "register", side_effect=RuntimeError(secret)):
            result = await self.post("register")
        self.assertEqual(result.status, 500)
        self.assertNotIn(secret, await result.text())

    def test_only_loopback_proxy_can_supply_client_ip(self):
        request = make_mocked_request("POST", "/api/auth/login", headers={
            "X-Mia-Client-IP": "198.51.100.10"})
        self.assertEqual(client_ip(request.clone(remote="127.0.0.1")), "198.51.100.10")
        self.assertEqual(client_ip(request.clone(remote="203.0.113.1")), "203.0.113.1")
        invalid = make_mocked_request("POST", "/", headers={"X-Mia-Client-IP": "forged"})
        self.assertEqual(client_ip(invalid.clone(remote="::1")), "::1")
