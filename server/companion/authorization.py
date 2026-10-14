"""Private scopes come from manager verification, never from device JSON."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import json
import re
from urllib.parse import urlsplit


class PrivateAuthorizationRequired(Exception):
    def __init__(self):
        super().__init__("请用智控台授权码完成授权")


@dataclass(frozen=True)
class AuthenticatedScope:
    owner: str
    operator_id: int
    user_id: int
    agent_id: str
    persona_id: str
    device_id: str
    client_id: str
    binding_version: int
    credential_version: int
    expires_at: datetime
    permissions: frozenset

    def snapshot(self):
        # No credential or model configuration is persisted with worker jobs.
        return {name: getattr(self, name) for name in (
            "owner", "operator_id", "device_id", "client_id", "binding_version", "credential_version")}


def _manager_scope(data):
    try:
        integers = ("operator_id", "user_id", "binding_version", "credential_version")
        if any(type(data[name]) is not int or data[name] < 1 for name in integers):
            raise ValueError()
        for name in ("agent_id", "device_id", "client_id"):
            if not isinstance(data[name], str) or not re.fullmatch(r"[A-Za-z0-9_:.-]{1,128}", data[name]):
                raise ValueError()
        if data["owner"] != f'user:{data["user_id"]}:agent:{data["agent_id"]}' or data["persona_id"] != "mia":
            raise ValueError()
        permissions = data["permissions"]
        allowed = {"memory:read", "memory:write", "memory:manage"}
        if not isinstance(permissions, list) or any(type(p) is not str or p not in allowed for p in permissions):
            raise ValueError()
        expiry = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError()
        return AuthenticatedScope(**{name: data[name] for name in (
            "owner", "operator_id", "user_id", "agent_id", "persona_id", "device_id", "client_id",
            "binding_version", "credential_version")}, expires_at=expiry, permissions=frozenset(permissions))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise PrivateAuthorizationRequired() from None


class PrivateAuthorization:
    def __init__(self, config):
        self.config = config

    async def _request(self, endpoint, body):
        # Reuse the existing server-secret client, with one bounded attempt.
        # Public HTTP is never permitted. Loopback is for isolated CI only;
        # an internal production transport must be reviewed before adding it.
        from config.manage_api_client import ManageApiClient

        try:
            manager = self.config["manager-api"]
            url = urlsplit(manager["url"])
            try:
                loopback = ipaddress.ip_address(url.hostname).is_loopback
            except ValueError:
                loopback = False
            if (url.scheme not in {"https", "http"} or (url.scheme == "http" and not loopback)
                    or url.username or url.password or url.query or url.fragment):
                raise PrivateAuthorizationRequired()
            client = ManageApiClient._get_instance()
            if client is None or client.config.get("url") != manager["url"]:
                raise PrivateAuthorizationRequired()
            return await asyncio.wait_for(client._async_request("POST", endpoint, json=body, timeout=3), timeout=3)
        except Exception:
            # Never propagate HTTP request bodies, credentials or provider errors.
            raise PrivateAuthorizationRequired() from None

    async def verify(self, device_id, client_id, credential):
        if not isinstance(credential, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", credential):
            raise PrivateAuthorizationRequired()
        scope = _manager_scope(await self._request("/config/mia-auth/verify", {
            "device_id": device_id, "client_id": client_id, "private_credential": credential}))
        if scope.device_id != device_id or scope.client_id != client_id:
            raise PrivateAuthorizationRequired()
        return scope

    async def restore(self, snapshot):
        # Persisted server-owned snapshots still require current manager proof.
        actual = _manager_scope(await self._request("/config/mia-auth/check-scope", snapshot))
        if actual.snapshot() != snapshot:
            raise PrivateAuthorizationRequired()
        return actual

    async def require(self, scope, permission):
        if (not isinstance(scope, AuthenticatedScope) or permission not in scope.permissions
                or scope.expires_at <= datetime.now(timezone.utc)):
            raise PrivateAuthorizationRequired()
        actual = await self.restore(scope.snapshot())
        if permission not in actual.permissions or actual != scope:
            raise PrivateAuthorizationRequired()
        return actual

    async def private_config(self, device_id, client_id, credential, selected_module):
        scope = await self.verify(device_id, client_id, credential)
        models = await self._request("/config/agent-models", {
            "macAddress": device_id, "clientId": client_id, "privateCredential": credential,
            "selectedModule": selected_module})
        if not isinstance(models, dict) or models.get("mia_owner") != scope.owner:
            raise PrivateAuthorizationRequired()
        if _manager_scope(models.get("mia_scope")) != scope:
            raise PrivateAuthorizationRequired()
        # Correct words cannot be loaded independently of private authorization.
        words = await self._request("/config/correct-words", {
            "macAddress": device_id, "clientId": client_id, "privateCredential": credential})
        if not isinstance(words, list) or any(not isinstance(word, str) for word in words):
            raise PrivateAuthorizationRequired()
        await self.require(scope, "memory:read")
        models["correct_words"] = words
        return scope, models


async def load_private_config(conn):
    conn._mia_scope = None
    conn._mia_owner = None
    conn._mia_authorization = PrivateAuthorization(conn.config)
    headers = conn.headers or {}
    credential = headers.pop("mia-private-credential", None)
    # A private header must arrive over TLS. A future TLS proxy requires an
    # independently verified trusted ingress, never X-Forwarded-Proto alone.
    transport = getattr(getattr(conn, "websocket", None), "transport", None)
    if credential and (transport is None or not transport.get_extra_info("ssl_object")):
        raise PrivateAuthorizationRequired()
    device = headers.get("device-id")
    client = headers.get("client-id", device)
    scope, config = await conn._mia_authorization.private_config(
        device, client, credential, conn.config["selected_module"])
    conn._mia_scope = scope
    conn._mia_owner = scope.owner
    return config


async def require_connection(conn, permission="memory:read"):
    if not getattr(conn, "read_config_from_api", False):
        return
    authorization = getattr(conn, "_mia_authorization", None)
    if not authorization:
        raise PrivateAuthorizationRequired()
    await authorization.require(getattr(conn, "_mia_scope", None), permission)


async def prompt_authorization(conn):
    await conn.websocket.send(json.dumps({
        "type": "mia_authorization", "status": "required",
        "message": "请用智控台授权码完成授权", "session_id": conn.session_id}, ensure_ascii=False))


async def route_required(conn, message):
    # Keep the transport hello available, but no personalized audio/text route.
    if isinstance(message, str) and len(message) <= 16384:
        try:
            request = json.loads(message)
        except (ValueError, RecursionError):
            request = None
        if isinstance(request, dict) and request.get("type") == "hello":
            from core.handle.textHandle import handleTextMessage
            await handleTextMessage(conn, message)
            await prompt_authorization(conn)


async def allow_output(conn):
    try:
        await require_connection(conn)
        return True
    except PrivateAuthorizationRequired:
        conn.client_abort = True
        if not getattr(conn, "_mia_authorization_required", False):
            conn._mia_authorization_required = True
            await prompt_authorization(conn)
        return False


def allow_generation(conn):
    # Upstream chat() runs in its executor, including recursive tool continuations.
    if not getattr(conn, "read_config_from_api", False):
        return True
    try:
        return asyncio.run_coroutine_threadsafe(allow_output(conn), conn.loop).result(timeout=4)
    except Exception:
        conn.client_abort = True
        return False


async def execute_tool(conn, tool_call):
    await require_connection(conn)
    return await conn.func_handler.handle_llm_function_call(conn, tool_call)
