"""Real SQLite contention and process death after a real result is persisted."""

import asyncio
import hashlib
import json
import os
import sqlite3
import time


def observe_commit(worker, control, root, report, lock, save):
    commit, resolve = worker.jobs.commit, worker.resolve

    async def observed_resolve(scope):
        with lock:
            report.setdefault('recovery_resolves', []).append({'pid': os.getpid()})
            save(report)
        return await resolve(scope)

    def observed_commit(job, result, vectors=None):
        source = json.loads(job['source_payload'])['text']
        if control.get('owner') != job['owner'] or control.get('source') != source or control.get('held'):
            return commit(job, result, vectors)
        control['held'] = True
        current = worker.jobs.current(job)
        assert current['state'] == 'validated' and json.loads(current['validated_result']) == result
        assert result['_schema'] == 1 and any(row['content'] == source and not row['sensitive']
            and row['kind'] == 'explicit' for row in result['memories'])
        assert vectors and report['extraction_outputs'], 'No genuine model result and BGE vector to recover'
        evidence = {'job_id': job['id'], 'pid': os.getpid(), 'state': current['state'],
            'attempts': current['attempts'], 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'result_sha256': hashlib.sha256(current['validated_result'].encode()).hexdigest(),
            'extraction_outputs': len(report['extraction_outputs']),
            'resolve_calls': len(report.get('recovery_resolves', [])), 'requests': report['requests']}
        temporary = root / 'recovery-ready.tmp'
        temporary.write_text(json.dumps(evidence))
        temporary.replace(root / 'recovery-ready.json')
        deadline = time.monotonic() + 20
        while not (root / 'recovery-release.json').exists():
            assert time.monotonic() < deadline, 'CI commit hold was not released'
            time.sleep(.02)
        try:
            return commit(job, result, vectors)
        except sqlite3.OperationalError as error:
            failure = {'job_id': job['id'], 'error_class': type(error).__name__,
                'database_locked': 'locked' in str(error).lower()}
            temporary = root / 'recovery-failed.tmp'
            temporary.write_text(json.dumps(failure))
            temporary.replace(root / 'recovery-failed.json')
            with lock:
                report['recovery_database_failure'] = failure
                save(report)
            raise

    worker.resolve, worker.jobs.commit = observed_resolve, observed_commit


async def fail_commit_and_crash(endpoint, tls, headers, root, source, crash):
    from websockets.asyncio.client import connect

    async def read_file(name, timeout):
        deadline = time.monotonic() + timeout
        path = root / name
        while not path.exists():
            assert time.monotonic() < deadline, 'Recovery observation timed out'
            await asyncio.sleep(.05)
        return json.loads(path.read_text())

    for name in ('ready', 'release', 'failed'):
        (root / ('recovery-' + name + '.json')).unlink(missing_ok=True)
    async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
        assert json.loads(await socket.recv())['type'] == 'hello'
        await socket.send(json.dumps({'type': 'test_chat', 'query': source, 'hold_commit': True}))
        answer = None
        while answer is None:
            value = json.loads(await asyncio.wait_for(socket.recv(), timeout=65))
            assert value['type'] != 'test_error'
            if value['type'] == 'test_reply':
                answer = value
        ready = await read_file('recovery-ready.json', 45)
        assert ready['job_id'] == answer['admission_status']['id']
        assert ready['source_sha256'] == hashlib.sha256(source.encode()).hexdigest()
        connection = sqlite3.connect(root / 'state.sqlite3', timeout=0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('BEGIN IMMEDIATE')  # Actual competing writer, no SQL or model stub.
            (root / 'recovery-release.json').write_text('{}')
            failure = await read_file('recovery-failed.json', 15)
            assert failure['job_id'] == ready['job_id'] and failure['database_locked']
            row = connection.execute('SELECT state,attempts,validated_result FROM mia_jobs WHERE id=?',
                (ready['job_id'],)).fetchone()
            assert row['state'] == 'validated' and row['attempts'] == ready['attempts']
            assert hashlib.sha256(row['validated_result'].encode()).hexdigest() == ready['result_sha256']
            assert connection.execute('SELECT COUNT(*) FROM memories').fetchone()[0] == 0
            await crash()  # Keep the real lock held until the original process is dead.
        finally:
            connection.rollback()
            connection.close()
            (root / 'recovery-release.json').write_text('{}')
        return {'ready': ready, 'failure': failure, 'source_session_id': answer['session_id'],
            'response_before_failure': answer['tts_text'], 'persisted_result_survived_failed_commit': True}
