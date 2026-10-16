"""Real grants, three fact owners, multi-device sharing and stale-grant rejection."""

import json
import os

import httpx


async def drive_scope(sample, ask, manage, peers):
    assert {peer['kind'] for peer in peers} == {'shared_device', 'other_agent', 'other_user'}
    shared = next(peer for peer in peers if peer['kind'] == 'shared_device')
    other_agent = next(peer for peer in peers if peer['kind'] == 'other_agent')
    other_user = next(peer for peer in peers if peer['kind'] == 'other_user')
    identities = [None, other_agent, other_user]
    facts, owners, sessions = [], [], []
    for index, peer in enumerate(identities):
        answer, saved = await ask(sample['sources'][index], peer=peer)
        sessions.append(answer['session_id'])
        assert len(saved['memories']) == 1, 'Owner store contained a foreign or unexpected fact'
        fact = saved['memories'][0]
        assert fact['content'] == sample['sources'][index] and fact['confirmed'] and fact['source']
        facts.append(fact)
        owners.append(saved['scope_snapshot']['owner'])
    assert len({fact['id'] for fact in facts}) == 3 and len(set(owners)) == 3

    async def recall(peer, index):
        answer, saved = await ask(sample['query'], peer=peer)
        sessions.append(answer['session_id'])
        assert answer['diagnostics']['selected_fact_ids'] == [facts[index]['id']]
        assert [fact['id'] for fact in saved['memories']] == [facts[index]['id']]
        assert saved['scope_snapshot']['owner'] == owners[index]
        assert sample['terms'][index] in answer['raw'] and sample['terms'][index] in answer['tts_text']
        serialized = json.dumps(answer['input'], ensure_ascii=False)
        for foreign in set(range(3)) - {index}:
            assert sample['terms'][foreign] not in serialized and sample['terms'][foreign] not in answer['raw']
        listed = await manage('list', peer=peer)
        assert [fact['id'] for fact in listed['memories']] == [facts[index]['id']]

    for peer, index in [(None, 0), (shared, 0), (other_agent, 1), (other_user, 2)]:
        await recall(peer, index)

    # These endpoints operate only on this test's temporary bound device. No
    # production SQL changes or client-provided owner/Scope bypass are used.
    base = os.environ['MIA_SCOPE_MANAGER_URL'].rstrip('/')
    token = os.environ['MIA_SCOPE_USER_TOKEN']
    async with httpx.AsyncClient(timeout=10, trust_env=False, verify=os.environ['MIA_SCOPE_CA']) as client:
        async def post(path, body, authorized=True):
            response = await client.post(base + path, json=body,
                headers={'Authorization': 'Bearer ' + token} if authorized else {})
            response.raise_for_status()
            value = response.json()
            assert value['code'] == 0, 'Isolated manager operation failed'
            return value.get('data')
        await post('/device/unbind', {'deviceId': shared['device_id']})
        await manage('list', expect_denial=True, peer=shared)
        await recall(None, 0)  # Unbinding one device does not delete the owner's facts.
        await post('/device/manual-add', {'agentId': other_agent['agent_id'], 'macAddress': shared['device_id'],
            'board': 'MIA_CI', 'appVersion': 'CI'})
        await manage('list', expect_denial=True, peer=shared)
        code = await post('/device/mia-auth/code', {'device_id': shared['device_id']})
        grant = await post('/device/mia-auth/exchange', {'device_id': shared['device_id'],
            'client_id': shared['client_id'], 'authorization_code': code['authorization_code']}, authorized=False)
        renewed = dict(shared, private_credential=grant['private_credential'])
        assert grant['scope']['owner'] == owners[1]
        await recall(renewed, 1)
        await manage('list', expect_denial=True, peer=shared)
    assert len(set(sessions)) == len(sessions)
    return {'source_ids': [fact['id'] for fact in facts], 'owners': owners,
        'session_ids': sessions, 'shared_device_recall': True, 'other_agent_and_user_isolated': True,
        'unbound_and_rebound_old_credential_rejected': True, 'rebound_new_scope_recall': True,
        'model_responses': 'actual selected provider; all raw answers require review',
        'scope': 'Three current fact owners; existing separate identity tests cover forged/expired snapshots and consumers; no iPhone claim'}
