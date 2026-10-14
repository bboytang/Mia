"""Called inside real manager tests; synthetic credentials only, never print them."""

import asyncio
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(os.environ['MIA_SCOPE_UPSTREAM']) / 'main/xiaozhi-server'))

from config.manage_api_client import ManageApiClient
from server.companion.authorization import (PrivateAuthorization, PrivateAuthorizationRequired,
    load_private_config, allow_generation, allow_output, execute_tool)


async def rejects(operation):
    try:
        await operation
    except PrivateAuthorizationRequired:
        return
    raise AssertionError('Unauthorized operation was accepted')


async def main():
    config = {'manager-api': {'url': os.environ['MIA_SCOPE_MANAGER_URL'],
                             'secret': os.environ['MIA_SCOPE_SERVER_SECRET']}, 'selected_module': {}}
    ManageApiClient(config)
    auth = PrivateAuthorization(config)
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
                      'real_model_acceptance': 'not_executed', 'actual_wss_acceptance': 'not_executed'}))


try:
    asyncio.run(main())
except Exception as error:
    print(json.dumps({'manager_python_scope_pass': False, 'error_class': type(error).__name__}))
    sys.exit(1)
finally:
    ManageApiClient.safe_close()
