"""Console proxy on the existing HTTP server; the manager proves every owner."""

import asyncio
import hmac
import json

from aiohttp import web

from .authorization import PrivateAuthorization, PrivateAuthorizationRequired
from .features import status, update
from .memory import MemoryError


class ManagementHandler:
    def __init__(self, config, *, store=None, authorization=None):
        self.config, self.store, self.authorization = config, store, authorization

    async def handle(self, request):
        secret = self.config.get('manager-api', {}).get('secret', '')
        header = request.headers.get('Authorization', '')
        if not isinstance(secret, str) or not secret or not hmac.compare_digest(header, 'Bearer ' + secret):
            raise web.HTTPUnauthorized()
        raw = bytearray()
        async for chunk in request.content.iter_chunked(4096):
            raw.extend(chunk)
            if len(raw) > 16384:
                raise web.HTTPRequestEntityTooLarge(max_size=16384, actual_size=len(raw))
        authorization = self.authorization or PrivateAuthorization(self.config)
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or set(data) != {'operator_id', 'agent_id', 'request'}:
                raise ValueError()
            proof = {'operator_id': data['operator_id'], 'agent_id': data['agent_id']}
            grant = await authorization._request('/config/mia-management/verify', proof)
            if not isinstance(grant, dict) or not isinstance(grant.get('owner'), str):
                raise PrivateAuthorizationRequired()
            owner = grant['owner']
            command = data['request']
            if not isinstance(command, dict):
                raise ValueError()
            action = command.get('action')
            if action not in {'status', 'pause', 'set_feature_settings', 'emotion_consent', 'reset_mia_emotion'}:
                raise ValueError()
            if self.store is None:
                from .xiaozhi_adapter import _store
                store = _store()
            else:
                store = self.store
            def apply():
                if action == 'reset_mia_emotion':
                    from .affect import reset
                    reset(store, owner)
                elif action == 'set_feature_settings':
                    update(store, owner, command.get('features'))
                elif action != 'status':
                    store.handle(owner, command)
                return status(store, owner)
            result = await asyncio.to_thread(apply)
            if await authorization._request('/config/mia-management/verify', proof) != grant:
                raise PrivateAuthorizationRequired()
            return web.json_response({'code': 0, 'data': result})
        except (PrivateAuthorizationRequired,):
            raise web.HTTPForbidden() from None
        except (ValueError, TypeError, KeyError, MemoryError):
            raise web.HTTPBadRequest() from None
        finally:
            if self.authorization is None:
                await authorization.close()
