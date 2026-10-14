"""Called inside real manager tests; synthetic credentials only, never print them."""

import asyncio
import json
import os
import ssl
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(os.environ['MIA_SCOPE_UPSTREAM']) / 'main/xiaozhi-server'))

from config.manage_api_client import ManageApiClient
from server.companion.authorization import (PrivateAuthorization, PrivateAuthorizationRequired,
    load_private_config, allow_generation, allow_output, execute_tool, server_tls_context)

trace = []


class TracedAuthorization(PrivateAuthorization):
    async def _request(self, endpoint, body):
        entry = {'endpoint': endpoint}
        trace.append(entry)
        result = await super()._request(endpoint, body)
        entry['result_type'] = type(result).__name__
        if endpoint == '/config/mia-auth/verify' and isinstance(result, dict):
            entry['field_types'] = {key: type(value).__name__ for key, value in result.items()}
            entry['binding_version'] = result.get('binding_version')
        return result


async def rejects(operation):
    try:
        await operation
    except PrivateAuthorizationRequired:
        return
    raise AssertionError('Unauthorized operation was accepted')


async def native_wss(config, device, client, credential):
    from websockets.asyncio.client import connect
    from websockets.asyncio.server import serve
    from core.auth import AuthManager

    transport_auth = AuthManager('synthetic-transport-only')
    legacy = transport_auth.generate_token(client, device)
    async def handler(socket):
        headers = dict(socket.request.headers)
        assert transport_auth.verify_token(headers.get('authorization', '')[7:],
            headers.get('client-id'), headers.get('device-id'))
        conn = SimpleNamespace(config=config, headers=headers, websocket=socket,
            read_config_from_api=True, session_id='native-tls-ci', client_abort=False)
        try:
            private = await load_private_config(conn)
            assert 'CI private prompt marker' in private['prompt']
            assert 'mia-private-credential' not in conn.headers
            await socket.send(json.dumps({'status': 'authorized'}))
            async for _ in socket:
                if await allow_output(conn):
                    await socket.send(json.dumps({'status': 'allowed'}))
        except PrivateAuthorizationRequired:
            await socket.send(json.dumps({'type': 'mia_authorization', 'status': 'required'}))

    async with serve(handler, '127.0.0.1', 0, ssl=server_tls_context()) as server:
        url = 'wss://127.0.0.1:' + str(server.sockets[0].getsockname()[1])
        verified = ssl.create_default_context(cafile=os.environ['MIA_SCOPE_CA'])
        headers = {'Device-Id': device, 'Client-Id': client, 'Authorization': 'Bearer ' + legacy}
        # Native TLS must verify a CA and address; no trust-all socket client.
        try:
            async with connect(url, ssl=ssl.create_default_context(), additional_headers=headers):
                raise AssertionError('Untrusted certificate accepted')
        except ssl.SSLCertVerificationError:
            pass
        async with connect(url, ssl=verified, additional_headers=headers) as socket:
            assert json.loads(await socket.recv())['status'] == 'required'
        headers['Mia-Private-Credential'] = credential
        async with connect(url, ssl=verified, additional_headers=headers) as socket:
            assert json.loads(await socket.recv())['status'] == 'authorized'
            await socket.send('check')
            assert json.loads(await socket.recv())['status'] == 'allowed'
            async with httpx.AsyncClient(timeout=3, trust_env=False) as http:
                response = await http.post(config['manager-api']['url'].rstrip('/') + '/device/mia-auth/revoke',
                    json={'device_id': device}, headers={'Authorization': 'Bearer ' + os.environ['MIA_SCOPE_USER_TOKEN']})
                assert response.json()['code'] == 0
            await socket.send('check')
            required = json.loads(await socket.recv())
            assert required['type'] == 'mia_authorization' and required['status'] == 'required'
    return True


async def main():
    config = {'manager-api': {'url': os.environ['MIA_SCOPE_MANAGER_URL'],
                             'secret': os.environ['MIA_SCOPE_SERVER_SECRET']}, 'selected_module': {}}
    ManageApiClient(config)
    auth = TracedAuthorization(config)
    device, client, credential = (os.environ[name] for name in (
        'MIA_SCOPE_DEVICE', 'MIA_SCOPE_CLIENT', 'MIA_SCOPE_CREDENTIAL'))
    scope, private = await auth.private_config(device, client, credential, {})
    assert private['mia_owner'] == scope.owner
    assert 'CI private prompt marker' in private['prompt']
    assert isinstance(private['correct_words'], list)
    assert credential not in json.dumps(scope.snapshot())
    await auth.require(scope, 'memory:manage')
    restored = await auth.restore(scope.snapshot())
    assert restored == scope
    forged = dict(scope.snapshot(), owner='user:999999999:agent:other')
    await rejects(auth.restore(forged))
    await rejects(auth.private_config(device, client, 'legacy-signature.timestamp', {}))
    await rejects(auth.private_config(device, 'other-client', credential, {}))
    conn = SimpleNamespace(config=config, headers={'device-id': device, 'client-id': client,
                           'mia-private-credential': credential}, websocket=SimpleNamespace(transport=None))
    await rejects(load_private_config(conn))
    assert 'mia-private-credential' not in conn.headers
    assert conn._mia_scope is None
    class Socket:
        async def send(self, message):
            assert json.loads(message)['type'] == 'mia_authorization'
    class Tool:
        calls = 0
        async def handle_llm_function_call(self, conn, request):
            self.calls += 1
            return 'synthetic tool output'
    tool = Tool()
    active = SimpleNamespace(_mia_scope=scope, _mia_authorization=auth, read_config_from_api=True,
        session_id='scope-ci', client_abort=False, websocket=Socket(), loop=asyncio.get_running_loop(), func_handler=tool)
    assert await asyncio.to_thread(allow_generation, active)
    assert await allow_output(active)
    assert await execute_tool(active, {'name': 'synthetic_tool'}) == 'synthetic tool output'
    tls_pass = await native_wss(config, device, client, credential) if os.environ.get('MIA_SCOPE_NATIVE_TLS') == 'true' else None
    # Actual manager revocation, using the existing authenticated console token.
    async with httpx.AsyncClient(timeout=3, trust_env=False) as http:
        response = await http.post(config['manager-api']['url'].rstrip('/') + '/device/mia-auth/revoke',
            json={'device_id': device}, headers={'Authorization': 'Bearer ' + os.environ['MIA_SCOPE_USER_TOKEN']})
        assert response.json()['code'] == 0
    await rejects(auth.require(scope, 'memory:read'))
    await rejects(auth.restore(scope.snapshot()))
    await rejects(auth.private_config(device, client, credential, {}))
    assert not await asyncio.to_thread(allow_generation, active)
    assert not await allow_output(active)
    await rejects(execute_tool(active, {'name': 'synthetic_tool'}))
    assert active.client_abort and tool.calls == 1
    print(json.dumps({'manager_python_scope_pass': True, 'checks': 17,
                      'native_wss_scope_pass': tls_pass,
                      'real_model_acceptance': 'not_executed', 'actual_ios_wss_acceptance': 'not_executed'}))


try:
    asyncio.run(main())
except Exception as error:
    print(json.dumps({'manager_python_scope_pass': False, 'error_class': type(error).__name__, 'request_trace': trace}))
    sys.exit(1)
finally:
    ManageApiClient.safe_close()
