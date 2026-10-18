"""Real persisted proposal, in-flight app SIGTERM, and fresh-process recovery."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import ssl
import threading
import time


def recovering():
    return os.environ.get('MIA_P23_SHUTDOWN_STAGE') == 'recover'


def guard_recovery_provider(report, persist):
    """Install before app.main/Worker.start, so startup recovery cannot evade it."""
    import core.utils.llm as llm
    original = llm.create_instance

    def factory(*args, **kwargs):
        provider = original(*args, **kwargs)

        def forbidden(*unused, **ignored):
            report['provider_requests'] += 1
            report['recovery_repeated_sdk'] = True
            persist(report)
            raise AssertionError('Persisted-result recovery attempted another model request')

        provider.client.chat.completions.create = forbidden
        return provider

    llm.create_instance = factory
    report['recovery_guard_before_launch'] = True
    persist(report)


async def open_driver(server, scopes, config, root, report, persist):
    from mia_behavior_runtime import observe_hold
    from mia_worker_competition import SOURCE, open_driver as open_probe

    driver = await open_probe(server, scopes, config, root, report, persist)
    observe_hold(server._mia_worker, {'stage': 'validated_vector', 'source': SOURCE,
        'owner': scopes[2].owner}, root, report, threading.RLock(), persist)
    report['shutdown_scope'] = 'CI hold after real BGE encoding and durable validated proposal; original Worker/app shutdown, no fabricated result'
    persist(report)
    return driver


def checkpoint(root, job_id):
    """Read durable state after a real child exit, without writing the database."""
    with sqlite3.connect((root / 'app-child/memory.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        row = db.execute('SELECT id,owner,state,attempts,validated_result FROM mia_jobs WHERE id=?', (job_id,)).fetchone()
        assert row is not None
        result = dict(row)
        raw = result.pop('validated_result')
        assert raw is not None or result['state'] == 'committed'
        assert raw is None or json.loads(raw)['_schema'] == 1
        result['validated_sha256'] = hashlib.sha256(raw.encode()).hexdigest() if raw is not None else None
        result['facts'] = [dict(x) for x in db.execute('SELECT m.id,m.owner,m.content,m.confirmed,'
            's.excerpt,v.dimension,v.normalized_vector FROM memories m JOIN sources s ON s.memory_id=m.id '
            'JOIN mia_vectors v ON v.memory_id=m.id WHERE m.owner=? AND s.session_id=?',
            (row['owner'], 'p23-worker-overlap'))]
        for fact in result['facts']:
            vector = fact.pop('normalized_vector')
            fact.update(vector_bytes=len(vector), vector_sha256=hashlib.sha256(vector).hexdigest())
        return result


async def drive(state, report, persist):
    root = Path(os.environ['MIA_P23_REPORT_DIR'])
    if recovering():
        before = report['inflight_shutdown']['checkpoint']
        deadline = time.monotonic() + 60
        while True:
            after = checkpoint(root, before['id'])
            if after['state'] == 'committed':
                break
            assert after['state'] not in ('failed', 'cancelled'), 'Durable recovery failed'
            assert time.monotonic() < deadline, 'Durable recovery did not commit'
            await asyncio.sleep(.05)
        report['recovery_checkpoint'] = after
        persist(report)
        return

    from core.auth import AuthManager
    from websockets.asyncio.client import connect

    peer = json.loads(os.environ['MIA_P23_PEERS'])[2]
    transport = AuthManager('synthetic-p23-latency-transport')
    headers = {'device-id': peer['device_id'], 'client-id': peer['client_id'],
        'authorization': 'Bearer ' + transport.generate_token(peer['client_id'], peer['device_id']),
        'mia-private-credential': peer['private_credential']}
    tls = ssl.create_default_context(cafile=os.environ['MIA_SCOPE_CA'])
    async with connect(f'wss://127.0.0.1:{state["worker_port"]}', ssl=tls, additional_headers=headers) as socket:
        await socket.send(json.dumps({'type': 'submit_probe'}))
        answer = json.loads(await asyncio.wait_for(socket.recv(), 10))
        assert answer['type'] == 'p23_worker'
        job_id = answer['probe']['admission']['id']
    deadline = time.monotonic() + 90
    held_path = root / 'app-child/shutdown-held.json'
    while not held_path.exists():
        current = job_state(root, job_id)
        assert current not in ('failed', 'cancelled', 'committed'), 'Task never entered genuine in-flight hold'
        assert time.monotonic() < deadline, 'No actual validated vector to hold'
        await asyncio.sleep(.02)
    evidence = json.loads(held_path.read_text())
    before = checkpoint(root, job_id)
    assert evidence['job_id'] == job_id and evidence['pid'] == state['pid']
    assert evidence['stage'] == 'validated_vector' and evidence['validated_actual_output']
    assert before['state'] == 'validated' and not before['facts']
    assert before['validated_sha256'] is not None
    report['inflight_held'] = evidence
    report['inflight_checkpoint_before_signal'] = before
    persist(report)


def job_state(root, job_id):
    with sqlite3.connect((root / 'app-child/memory.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        return db.execute('SELECT state FROM mia_jobs WHERE id=?', (job_id,)).fetchone()[0]


def after_exit(root, report, persist):
    child = json.loads((root / 'app-child/app-results.json').read_text())
    if not recovering():
        held = report['inflight_held']
        after = checkpoint(root, held['job_id'])
        before = report['inflight_checkpoint_before_signal']
        assert after['state'] in ('validated', 'retry_wait') and not after['facts']
        assert after['attempts'] == before['attempts'] == held['persisted_attempts']
        assert after['validated_sha256'] == before['validated_sha256']
        assert 1 <= child['provider_requests'] == after['attempts'] <= 2
        assert not child.get('provider_errors') and not child.get('case_errors')
        assert not child['app_shutdowns'][0]['native_finished'], 'No actual native work remained at app shutdown'
        report['inflight_shutdown'] = {'pid': child['pid'], 'seconds': report['app_process_shutdown_seconds'],
            'returncode': report['app_returncode'], 'provider_requests': child['provider_requests'],
            'checkpoint': after, 'scope': 'Entire app WS/HTTP/GC/Worker process; Java/databases remain live for restart, not all-service in-flight shutdown'}
        assert report['inflight_shutdown']['seconds'] <= 20
        persist(report)
        persist_child = root / 'shutdown-inflight-child.json'
        persist_child.write_bytes((root / 'app-child/app-results.json').read_bytes())
        return
    before = report['inflight_shutdown']['checkpoint']
    after = checkpoint(root, before['id'])
    assert child['pid'] != report['inflight_shutdown']['pid']
    assert child.get('recovery_guard_before_launch') and not child.get('recovery_repeated_sdk')
    assert child['provider_requests'] == child['accepted_extraction_jobs'] == 0
    assert after['state'] == 'committed' and after['attempts'] == before['attempts']
    # The original atomic commit intentionally clears the durable proposal.
    assert after['validated_sha256'] is None
    assert len(after['facts']) == 1
    fact = after['facts'][0]
    from mia_worker_competition import SOURCE
    assert fact['owner'] == before['owner'] and fact['content'] == fact['excerpt'] == SOURCE
    assert fact['confirmed'] and fact['dimension'] == 768 and fact['vector_bytes'] == 3072
    assert fact['vector_sha256'] == report['inflight_held']['actual_vector_sha256']
    report['worker_contract_passed'] = True
    report['inflight_app_shutdown_recovery_passed'] = True
    report['recovery_checkpoint'] = after
    persist(report)
