import asyncio
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from server.account_store import AccountError, AccountStore, password_digest


PASSWORD = "test password preserved 123 "


class AccountStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "accounts.sqlite3"
        self.now = [1_800_000_000]
        self.store = AccountStore(self.path, clock=lambda: self.now[0])

    async def asyncTearDown(self):
        await self.store.close()
        self.temp.cleanup()

    async def test_registration_login_and_protected_storage(self):
        first = await self.store.register("Ｍia_朋友", PASSWORD)
        second = await self.store.register("another", PASSWORD)
        self.assertEqual(first["username"], "mia_朋友")
        self.assertEqual(first["expires_at"], 1_802_592_000)
        user_id = self.store.authenticate(first["token"])
        self.assertIsNotNone(user_id)
        logged_in = await self.store.login("MIA_朋友", PASSWORD)
        self.assertEqual(self.store.authenticate(logged_in["token"]), user_id)
        rows = self.store.db.execute("SELECT salt,password_hash FROM users").fetchall()
        self.assertNotEqual(rows[0]["salt"], rows[1]["salt"])
        self.assertTrue(all(len(row["salt"]) == 16 for row in rows))
        self.assertTrue(all(len(row["password_hash"]) == 32 for row in rows))
        digests = {row[0] for row in self.store.db.execute("SELECT token_hash FROM sessions")}
        self.assertIn(hashlib.sha256(first["token"].encode()).hexdigest(), digests)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        raw = b"".join(p.read_bytes() for p in self.path.parent.glob("accounts.sqlite3*"))
        for secret in [PASSWORD, first["token"], second["token"]]:
            self.assertNotIn(secret.encode(), raw)

    async def test_validation_and_duplicate_normalized_username(self):
        for username, password in [("ab", PASSWORD), ("has space", PASSWORD),
                                   ("abc", "short"), ("abc", "x" * 129),
                                   ("abc", 3), ("x" * 33, PASSWORD)]:
            with self.subTest(username=username):
                with self.assertRaises(AccountError) as error:
                    await self.store.register(username, password)
                self.assertEqual(error.exception.status, 400)
        await self.store.register("ＭＩＡ", PASSWORD)
        with self.assertRaises(AccountError) as error:
            await self.store.register("mia", PASSWORD)
        self.assertEqual(error.exception.status, 409)
        errors = []
        for name in ["mia", "missing"]:
            with self.assertRaises(AccountError) as error:
                await self.store.login(name, PASSWORD + "wrong")
            errors.append((error.exception.status, error.exception.code, str(error.exception)))
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[0][0], 401)
        with self.assertRaises(AccountError):
            await self.store.login("mia", PASSWORD.strip())

    async def test_expiry_revocation_and_reopen(self):
        item = await self.store.register("persistent", PASSWORD)
        await self.store.close()
        self.store = AccountStore(self.path, clock=lambda: self.now[0])
        self.assertIsNotNone(self.store.authenticate(item["token"]))
        self.now[0] = item["expires_at"]
        self.assertIsNone(self.store.authenticate(item["token"]))
        new = await self.store.login("persistent", PASSWORD)
        self.store.revoke(new["token"])
        self.store.revoke(new["token"])
        self.assertIsNone(self.store.authenticate(new["token"]))

    async def test_user_limit_and_racing_registration_are_atomic(self):
        self.store.max_users = 1
        results = await asyncio.gather(self.store.register("first", PASSWORD),
                                       self.store.register("second", PASSWORD),
                                       return_exceptions=True)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM users").fetchone()[0], 1)
        rejected = next(result for result in results if isinstance(result, AccountError))
        self.assertEqual(rejected.status, 429)

    async def test_duplicate_race_and_session_limit(self):
        results = await asyncio.gather(self.store.register("same", PASSWORD),
                                       self.store.register("ＳＡＭＥ", PASSWORD),
                                       return_exceptions=True)
        first = next(result for result in results if isinstance(result, dict))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(next(r for r in results if isinstance(r, AccountError)).status, 409)
        latest = first
        for _ in range(5):
            latest = await self.store.login("same", PASSWORD)
        self.assertIsNone(self.store.authenticate(first["token"]))
        self.assertIsNotNone(self.store.authenticate(latest["token"]))
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM sessions").fetchone()[0], 5)

    async def test_daily_limit_persists_and_resets_on_utc_day(self):
        self.store.daily_rounds = 2
        item = await self.store.register("speaker", PASSWORD)
        user = self.store.authenticate(item["token"])
        self.store.consume_round(user)
        self.store.consume_round(user)
        with self.assertRaises(AccountError) as error:
            self.store.consume_round(user)
        self.assertEqual(error.exception.status, 429)
        await self.store.close()
        self.store = AccountStore(self.path, daily_rounds=2, clock=lambda: self.now[0])
        with self.assertRaises(AccountError):
            self.store.consume_round(user)
        self.now[0] += 86_400
        self.store.consume_round(user)

    async def test_admin_reset_revokes_sessions_and_preserves_password_spaces(self):
        item = await self.store.register("reset_user", PASSWORD)
        new_password = " replacement password 456 "
        await self.store.reset_password("RESET_USER", new_password)
        self.assertIsNone(self.store.authenticate(item["token"]))
        with self.assertRaises(AccountError):
            await self.store.login("reset_user", PASSWORD)
        new = await self.store.login("reset_user", new_password)
        self.assertIsNotNone(self.store.authenticate(new["token"]))

    async def test_cancelled_hash_keeps_real_concurrency_slot(self):
        release = threading.Event()
        started = threading.Event()
        count = [0]
        lock = threading.Lock()

        def blocked(password, salt):
            with lock:
                count[0] += 1
                if count[0] == 2:
                    started.set()
            release.wait(timeout=5)
            return password_digest(password, salt)

        with patch("server.account_store.password_digest", blocked):
            first = asyncio.create_task(self.store.register("cancelled", PASSWORD))
            second = asyncio.create_task(self.store.register("running", PASSWORD))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                first.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await first
                with self.assertRaises(AccountError) as error:
                    await self.store.register("third", PASSWORD)
                self.assertEqual(error.exception.status, 429)
            finally:
                release.set()
                await second
        await asyncio.sleep(0)
        item = await self.store.register("after_finish", PASSWORD)
        self.assertIsNotNone(self.store.authenticate(item["token"]))
        self.assertEqual(self.store.db.execute(
            "SELECT count(*) FROM users WHERE username='cancelled'").fetchone()[0], 0)
