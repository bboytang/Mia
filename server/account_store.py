"""Protected SQLite accounts and revocable, opaque voice sessions."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import time
import unicodedata


class AccountError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code


def normalized_username(username):
    if not isinstance(username, str):
        raise AccountError(400, "invalid_input", "用户名格式不正确")
    value = unicodedata.normalize("NFKC", username).casefold()
    if not 3 <= len(value) <= 32 or not all(c.isalnum() or c == "_" for c in value):
        raise AccountError(400, "invalid_input", "用户名需为 3–32 个字母、汉字、数字或下划线")
    return value


def valid_password(password):
    if not isinstance(password, str) or not 15 <= len(password) <= 128:
        raise AccountError(400, "invalid_input", "密码需为 15–128 个字符")
    return password


def password_digest(password, salt):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**15,
                          r=8, p=3, dklen=32, maxmem=64 * 1024 * 1024)


class AccountStore:
    def __init__(self, path, max_users=100, daily_rounds=30, clock=time.time):
        if max_users < 1 or daily_rounds < 1:
            raise ValueError("账号数量和每日轮数必须大于零")
        self.max_users = max_users
        self.daily_rounds = daily_rounds
        self.clock = clock
        path = Path(path)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(path, 0o600)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id)
                ON DELETE CASCADE, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                day TEXT NOT NULL, rounds INTEGER NOT NULL, PRIMARY KEY(user_id,day)
            );
        """)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mia-auth")
        self._jobs = set()
        self._dummy_salt = secrets.token_bytes(16)
        self._closed = False

    async def _hash(self, password, salt):
        if len(self._jobs) >= 2:
            raise AccountError(429, "busy", "登录服务繁忙，请稍后重试")
        job = asyncio.get_running_loop().run_in_executor(
            self._executor, password_digest, password, salt)
        self._jobs.add(job)

        def finished(future):
            self._jobs.discard(future)
            if not future.cancelled():
                future.exception()

        job.add_done_callback(finished)
        # Cancellation stops the request, not the running scrypt thread or its slot.
        return await asyncio.shield(job)

    def _session(self, user_id, username):
        now = int(self.clock())
        self.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        token = secrets.token_urlsafe(32)
        expiry = now + 30 * 86_400
        self.db.execute("INSERT INTO sessions VALUES (?,?,?)",
                        (self._token_hash(token), user_id, expiry))
        self.db.execute("""DELETE FROM sessions WHERE user_id=? AND token_hash NOT IN
            (SELECT token_hash FROM sessions WHERE user_id=? ORDER BY rowid DESC LIMIT 5)
        """, (user_id, user_id))
        return {"username": username, "token": token, "expires_at": expiry}

    async def register(self, username, password):
        username = normalized_username(username)
        password = valid_password(password)
        salt = secrets.token_bytes(16)
        digest = await self._hash(password, salt)
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                if self.db.execute("SELECT count(*) FROM users").fetchone()[0] >= self.max_users:
                    raise AccountError(429, "registration_closed", "账号名额已满，请联系管理员")
                cursor = self.db.execute("""INSERT INTO users
                    (username,salt,password_hash,created_at) VALUES (?,?,?,?)""",
                    (username, salt, digest, int(self.clock())))
                return self._session(cursor.lastrowid, username)
        except sqlite3.IntegrityError:
            raise AccountError(409, "username_taken", "用户名已被使用") from None

    async def login(self, username, password):
        username = normalized_username(username)
        password = valid_password(password)
        user = self.db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        digest = await self._hash(password, user["salt"] if user else self._dummy_salt)
        if user is None or not hmac.compare_digest(digest, user["password_hash"]):
            raise AccountError(401, "invalid_credentials", "用户名或密码不正确")
        # An administrator may have reset the password while scrypt ran.
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            current = self.db.execute("SELECT password_hash FROM users WHERE id=?",
                                      (user["id"],)).fetchone()
            if current is None or not hmac.compare_digest(digest, current[0]):
                raise AccountError(401, "invalid_credentials", "用户名或密码不正确")
            return self._session(user["id"], user["username"])

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def authenticate(self, token):
        if not isinstance(token, str) or not 1 <= len(token) <= 256:
            return None
        row = self.db.execute("SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?",
                              (self._token_hash(token), int(self.clock()))).fetchone()
        return row[0] if row else None

    def revoke(self, token):
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE token_hash=?", (self._token_hash(token),))

    def consume_round(self, user_id):
        day = datetime.fromtimestamp(self.clock(), timezone.utc).date().isoformat()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT rounds FROM usage WHERE user_id=? AND day=?",
                                  (user_id, day)).fetchone()
            if row and row[0] >= self.daily_rounds:
                raise AccountError(429, "daily_limit", "今日语音额度已用完，请明天再来")
            self.db.execute("""INSERT INTO usage VALUES (?,?,1)
                ON CONFLICT(user_id,day) DO UPDATE SET rounds=rounds+1""", (user_id, day))

    async def reset_password(self, username, password):
        username = normalized_username(username)
        password = valid_password(password)
        salt = secrets.token_bytes(16)
        digest = await self._hash(password, salt)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if row is None:
                raise AccountError(404, "unknown_account", "账号不存在")
            self.db.execute("UPDATE users SET salt=?,password_hash=? WHERE id=?",
                            (salt, digest, row[0]))
            self.db.execute("DELETE FROM sessions WHERE user_id=?", (row[0],))

    async def close(self):
        if self._closed:
            return
        self._closed = True
        if self._jobs:
            await asyncio.gather(*(asyncio.shield(job) for job in tuple(self._jobs)),
                                 return_exceptions=True)
        self._executor.shutdown(wait=True)
        self.db.close()
