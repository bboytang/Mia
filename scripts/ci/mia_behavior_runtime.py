"""Actual installed app/services; only CI configuration and native hold are controlled."""

import asyncio
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import time


def configuration():
    ports = []
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            ports.append(listener.getsockname()[1])
    assert ports[0] != ports[1]
    return {'read_config_from_api': True, 'selected_module': {},
            'server': {'ip': '127.0.0.1', 'port': ports[0], 'http_port': ports[1],
                       'auth_key': 'synthetic-lifecycle-transport', 'auth': {'enabled': True}},
            'manager-api': {'url': os.environ['MIA_SCOPE_MANAGER_URL'],
                            'secret': os.environ['MIA_SCOPE_SERVER_SECRET']},
            'log': {'log_level': 'CRITICAL', 'log_dir': '/tmp/mia-runtime-logs',
                    'data_dir': '/tmp/mia-runtime-data'}}


def bootstrap():
    # Select synthetic CI configuration through the original configuration cache.
    # No fake config.logger/util modules, no production file or secret lookup.
    from core.utils.cache.manager import cache_manager, CacheType
    from config import settings
    config = configuration()
    cache_manager.set(CacheType.CONFIG, 'main_config', config)
    settings.config_file_valid = True  # No production/local config file in this fixture.
    from config.logger import setup_logging
    logger = setup_logging(config)
    logger.remove()  # Do not retain exception-local diagnostics containing CI credentials.
    logger.add(lambda message: None, level='CRITICAL', diagnose=False, backtrace=False)
    return config, logger


async def launch(config, root, report, lock, save):
    from mia_companion import xiaozhi_adapter as adapter
    app = importlib.import_module('app')
    from core.utils.gc_manager import get_gc_manager
    loop = asyncio.get_running_loop()
    captured = loop.create_future()
    original_start, original_stop = adapter.start_worker, adapter.stop_service

    async def start(server):
        await original_start(server)
        assert server.config is config and server._mia_worker is not None
        captured.set_result(server)

    async def stop(server, gc_manager, tasks, timeout=20):
        started = time.monotonic()
        drained = await original_stop(server, gc_manager, tasks, timeout=timeout)
        with lock:
            report.setdefault('app_shutdowns', []).append({
                'pid': os.getpid(), 'budget_seconds': timeout,
                'cleanup_seconds': time.monotonic() - started, 'drained': drained,
                'worker_closing': server._mia_worker.closing,
                'worker_task_done': server._mia_worker.task.done(),
                'gc_stopped': gc_manager._task is None,
                'service_tasks_done': [task.done() for task in tasks if task is not None],
                'native_finished': server._mia_worker.lane.done.is_set()})
            save(report)
        assert server._mia_worker.closing and server._mia_worker.task.done()
        assert gc_manager._task is None and all(task.done() for task in tasks if task is not None)
        return drained

    adapter.start_worker, adapter.stop_service = start, stop
    task = asyncio.create_task(app.main(), name='actual-installed-app-main')
    try:
        done, _ = await asyncio.wait({task, captured}, timeout=30, return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            await task
            raise AssertionError('Actual app exited before Worker startup')
        assert captured in done, 'Actual app Worker startup timed out'
        server = captured.result()
        deadline = time.monotonic() + 15
        ports = [config['server']['port'], config['server']['http_port']]
        while True:
            assert not task.done(), 'Actual app exited before sockets became ready'
            connected = []
            for port in ports:
                try:
                    reader, writer = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', port), 1)
                    writer.close()
                    await writer.wait_closed()
                    connected.append(port)
                except (OSError, asyncio.TimeoutError):
                    pass
            if connected == ports:
                break
            assert time.monotonic() < deadline, 'Actual WS/HTTP sockets did not start'
            await asyncio.sleep(.05)
        gc = get_gc_manager()
        assert gc._task is not None and not gc._task.done()
        service_tasks = {task.get_coro().__qualname__ for task in asyncio.all_tasks() if not task.done()}
        assert {'WebSocketServer.start', 'SimpleHttpServer.start'}.issubset(service_tasks)
        with lock:
            report.setdefault('app_lifecycles', []).append({
                'pid': os.getpid(), 'ports': ports, 'gc_running': True,
                'actual_service_tasks': sorted(name for name in service_tasks if name in {'WebSocketServer.start', 'SimpleHttpServer.start'}),
                'app_sha256': hashlib.sha256(Path(app.__file__).read_bytes()).hexdigest(),
                'server_class': type(server).__module__ + '.' + type(server).__name__,
                'worker_class': type(server._mia_worker).__module__ + '.' + type(server._mia_worker).__name__,
                'scope': 'Actual app.main, WebSocketServer, SimpleHttpServer, GC and original Worker; separate synthetic WSS text driver; audio consumers omitted'})
            save(report)
        return server, task
    except BaseException:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise


def observe_hold(worker, control, root, report, lock, save):
    from mia_companion.extraction import normalize, validate_output
    original = worker.resolve

    async def resolve(scope):
        extractor = await original(scope)

        def extract(sources, context):
            value = extractor(sources, context)
            if sources != [control.get('source')]:
                return value
            result = validate_output(value, sources, context)
            assert any(row['content'] == normalize(sources[0]) and row['kind'] == 'explicit'
                       and not row['sensitive'] for row in result['memories'])
            with worker.jobs.store.lock:
                rows = worker.jobs.store.db.execute(
                    "SELECT id,source_payload FROM mia_jobs WHERE owner=? AND state='extracting'", (scope.owner,)).fetchall()
            job_ids = [row['id'] for row in rows if json.loads(row['source_payload'])['text'] == normalize(sources[0])]
            assert len(job_ids) == 1, 'Held proposal is not bound to one actual active job'
            evidence = {'source_sha256': hashlib.sha256(sources[0].encode()).hexdigest(),
                        'validated_actual_output': True, 'pid': os.getpid(), 'job_id': job_ids[0]}
            temporary = root / 'shutdown-held.tmp'
            temporary.write_text(json.dumps(evidence))
            temporary.replace(root / 'shutdown-held.json')
            with lock:
                report.setdefault('shutdown_held_outputs', []).append(evidence)
                save(report)
            deadline = time.monotonic() + 45
            while not (root / 'shutdown-release.json').exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError('Controlled CI native hold expired')
                time.sleep(.02)
            return value

        return extract

    worker.resolve = resolve


async def drive_shutdown(sample, endpoint_state, tls, headers, root, ask, start, stop, first_pid):
    from websockets.asyncio.client import connect
    import sqlite3

    async def held(source, release):
        for name in ('shutdown-held.json', 'shutdown-release.json'):
            (root / name).unlink(missing_ok=True)
        async with connect(endpoint_state(), ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            hello = json.loads(await socket.recv())
            assert hello['type'] == 'hello'
            await socket.send(json.dumps({'type': 'test_chat', 'query': source, 'shutdown_hold': True}))
            answer = None
            deadline = time.monotonic() + 65
            while answer is None or not (root / 'shutdown-held.json').exists():
                assert time.monotonic() < deadline, 'No genuine held extraction'
                if answer is None:
                    value = json.loads(await asyncio.wait_for(socket.recv(), 65))
                    assert value['type'] != 'test_error'
                    if value['type'] == 'test_reply':
                        answer = value
                else:
                    await asyncio.sleep(.05)
            evidence = json.loads((root / 'shutdown-held.json').read_text())
            assert evidence['source_sha256'] == hashlib.sha256(source.encode()).hexdigest()
            job_id = answer['admission_status']['id']
            assert evidence['job_id'] == job_id and evidence['pid'] == hello['pid']

            async def release_later():
                await asyncio.sleep(1)
                (root / 'shutdown-release.json').write_text('{}')

            releasing = asyncio.create_task(release_later()) if release else None
            started = time.monotonic()
            try:
                await stop()
            finally:
                if releasing:
                    await releasing
            duration = time.monotonic() - started
            assert duration <= 20, 'Actual entire process exceeded twenty-second shutdown'
        with sqlite3.connect('file:' + (root / 'state.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
            state, attempts = db.execute('SELECT state,attempts FROM mia_jobs WHERE id=?', (job_id,)).fetchone()
        assert 1 <= attempts <= 2
        if release:
            assert state == 'committed'
        else:
            assert attempts == 1, 'No native extraction attempt remains for genuine restart recovery'
            assert state in {'extracting', 'pending', 'retry_wait', 'validated'}
        return {'job_id': job_id, 'pid': evidence['pid'], 'release_during_shutdown': release,
                'shutdown_seconds': duration, 'state_after_exit': state, 'attempts_after_exit': attempts,
                'answer': answer['tts_text']}

    drained = await held(sample['drain_source'], True)
    second_pid = await start()
    assert second_pid != first_pid
    recalled, saved = await ask(sample['drain_query'])
    assert sample['drain_term'] in recalled['tts_text'] and len(saved['memories']) == 1
    blocked = await held(sample['blocked_source'], False)
    third_pid = await start()
    assert len({first_pid, second_pid, third_pid}) == 3
    deadline = time.monotonic() + 55
    while True:
        with sqlite3.connect('file:' + (root / 'state.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
            state = db.execute('SELECT state FROM mia_jobs WHERE id=?', (blocked['job_id'],)).fetchone()[0]
        if state == 'committed':
            break
        assert state not in {'failed', 'cancelled'} and time.monotonic() < deadline, 'Original recovered task did not commit'
        await asyncio.sleep(.1)
    recalled, saved = await ask(sample['blocked_query'])
    assert sample['blocked_term'] in recalled['tts_text'] and len(saved['memories']) == 2
    with sqlite3.connect('file:' + (root / 'state.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
        state, attempts = db.execute('SELECT state,attempts FROM mia_jobs WHERE id=?', (blocked['job_id'],)).fetchone()
        assert state == 'committed' and 1 <= attempts <= 2
        assert db.execute('SELECT COUNT(*) FROM memories').fetchone()[0] == 2
        assert db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0] == 2
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    return {'drained': drained, 'blocked': blocked, 'recovered_job_state': state,
            'recovered_attempts': attempts, 'server_pids': [first_pid, second_pid, third_pid],
            'scope': 'Actual installed app/service lifecycle with real manager, model, BGE and SQLite; controlled native hold; no audio consumers or P23 resource claim'}
