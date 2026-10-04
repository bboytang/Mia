"""Loopback-only account HTTP routes; Caddy provides external TLS."""

from collections import deque
import ipaddress
import time

from aiohttp import web

from server.account_store import AccountError, normalized_username


def client_ip(request):
    remote = request.remote or "unknown"
    try:
        if ipaddress.ip_address(remote).is_loopback:
            return str(ipaddress.ip_address(request.headers.get("X-Mia-Client-IP", remote)))
    except ValueError:
        pass
    return remote


class AttemptLimiter:
    def __init__(self, clock):
        self.clock = clock
        self.buckets = {}

    def hit(self, key, limit):
        now = self.clock()
        # ponytail: bounded 4096-bucket scan; replace with an expiry queue if traffic grows.
        for existing, times in list(self.buckets.items()):
            while times and times[0] <= now - 60:
                times.popleft()
            if not times:
                del self.buckets[existing]
        if key not in self.buckets and len(self.buckets) >= 4096:
            raise AccountError(429, "rate_limit", "尝试过于频繁，请稍后重试")
        times = self.buckets.setdefault(key, deque())
        if len(times) >= limit:
            raise AccountError(429, "rate_limit", "尝试过于频繁，请稍后重试")
        times.append(now)


def create_app(store, clock=time.monotonic):
    limiter = AttemptLimiter(clock)

    @web.middleware
    async def errors(request, handler):
        try:
            response = await handler(request)
        except AccountError as error:
            response = web.json_response({"error": error.code, "message": str(error)},
                                         status=error.status)
            if error.status == 429:
                response.headers["Retry-After"] = "60"
        except web.HTTPException as error:
            response = web.json_response({"error": "invalid_request", "message": "请求格式不正确"},
                                         status=error.status)
        except Exception:
            response = web.json_response({"error": "unavailable", "message": "账号服务暂时不可用"},
                                         status=500)
        response.headers["Cache-Control"] = "no-store"
        return response

    async def credentials(request):
        limiter.hit(("ip", client_ip(request)), 20)
        if request.content_type != "application/json":
            raise AccountError(415, "invalid_input", "请使用 JSON 请求")
        try:
            body = await request.json()
        except (ValueError, UnicodeError):
            raise AccountError(400, "invalid_input", "请求格式不正确") from None
        if not isinstance(body, dict) or set(body) != {"username", "password"}:
            raise AccountError(400, "invalid_input", "请输入用户名和密码")
        username = normalized_username(body["username"])
        limiter.hit(("username", username), 10)
        return username, body["password"]

    async def register(request):
        username, password = await credentials(request)
        return web.json_response(await store.register(username, password), status=201)

    async def login(request):
        username, password = await credentials(request)
        return web.json_response(await store.login(username, password))

    async def logout(request):
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            store.revoke(authorization[7:])
        return web.Response(status=204)

    app = web.Application(client_max_size=4096, middlewares=[errors])
    app.router.add_post("/api/auth/register", register)
    app.router.add_post("/api/auth/login", login)
    app.router.add_post("/api/auth/logout", logout)
    return app
