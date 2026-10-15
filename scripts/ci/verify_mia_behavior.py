"""First P22 composed real-manager/BGE/provider gate; other B01-B08 gates remain explicit.

Only synthetic CI users. The WSS harness drives the installed reply/completion
bridge; it omits microphone/TTS consumers, not model or embedding responses.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
from queue import Queue
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
import traceback
from types import ModuleType, SimpleNamespace
import uuid

import httpx

sys.path.insert(0, str(Path(os.environ['MIA_SCOPE_UPSTREAM']) / 'main/xiaozhi-server'))
os.chdir(Path(os.environ['MIA_SCOPE_UPSTREAM']) / 'main/xiaozhi-server')
logger = SimpleNamespace()
logger.bind = lambda *args, **kwargs: logger
for level in ('debug', 'info', 'warning', 'error'):
    setattr(logger, level, lambda *args, **kwargs: None)
logging = ModuleType('config.logger')
logging.setup_logging = lambda: logger
sys.modules['config.logger'] = logging
util = ModuleType('core.utils.util')
util.check_model_key = lambda *args, **kwargs: None
sys.modules['core.utils.util'] = util

from config.manage_api_client import ManageApiClient
from core.auth import AuthManager
from core.utils.dialogue import Dialogue, Message
from core.utils.llm import create_instance
from mia_companion.authorization import PrivateAuthorizationRequired, load_private_config
from mia_companion.context import ContextBuilder
from mia_companion.persona import PersonaGuardrail
from mia_companion.semantic import SemanticMemoryIndex
from mia_companion import reply, xiaozhi_adapter as adapter


ROOT = Path(os.environ['MIA_BEHAVIOR_DIR']) / ('round-' + os.environ['MIA_BEHAVIOR_ROUND'])
REPORT = ROOT / 'results.json'
LOCK = threading.Lock()


def save(report):
    # Reports never contain raw model configuration or private credentials.
    text = json.dumps(report, ensure_ascii=False, indent=2)
    for name in ('MIA_TEST_LLM_API_KEY', 'MIA_SCOPE_CREDENTIAL', 'MIA_SCOPE_SERVER_SECRET', 'MIA_SCOPE_USER_TOKEN'):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, '[REDACTED]')
    REPORT.write_text(text + '\n')


def selected_provider(configuration, report, purpose):
    assert configuration['api_key'] == os.environ['MIA_TEST_LLM_API_KEY']
    assert configuration['model_name'] == os.environ['MIA_TEST_LLM_MODEL']
    assert configuration['base_url'] == os.environ['MIA_TEST_LLM_BASE_URL']
    provider = create_instance(configuration['type'], configuration)
    original = provider.client
    provider.client = original.with_options(max_retries=0, http_client=httpx.Client(timeout=30, follow_redirects=False))
    original.close()
    create = provider.client.chat.completions.create

    def counted(*args, **kwargs):
        with LOCK:
            assert report['requests'] < 18, 'Per-round real request budget exhausted'
            report['requests'] += 1
            report['request_kinds'].append(purpose)
            save(report)
        return create(*args, **kwargs)

    provider.client.chat.completions.create = counted
    if purpose == 'extraction':
        response = provider.response_no_stream

        def captured(*args, **kwargs):
            value = response(*args, **kwargs)
            with LOCK:
                report['extraction_outputs'].append(value)
                save(report)
            return value

        provider.response_no_stream = captured
    return provider


async def serve():
    from websockets.asyncio.server import serve as wss
    report = json.loads(REPORT.read_text())
    configuration = {'read_config_from_api': True, 'manager-api': {'url': os.environ['MIA_SCOPE_MANAGER_URL'],
                                   'secret': os.environ['MIA_SCOPE_SERVER_SECRET']}, 'selected_module': {}}
    ManageApiClient(configuration)
    os.environ['MIA_MEMORY_DB'] = str(ROOT / 'state.sqlite3')
    # Observe the production factory without replacing its responses. The
    # installed lifecycle still restores Scope and chooses the Worker model.
    import core.utils.llm as existing_llm
    def observed_factory(name, model):
        assert name == model['type'] == 'openai'
        return selected_provider(model, report, 'extraction')
    existing_llm.create_instance = observed_factory
    runtime = SimpleNamespace(config=configuration)
    await adapter.start_worker(runtime)
    worker = runtime._mia_worker
    store = worker.jobs.store
    index = SemanticMemoryIndex(store, reply._encoder)
    transport = AuthManager('synthetic-behavior-transport')

    @adapter.completed_chat
    def chat(conn, query, depth=0):
        adapter.begin_turn(conn, query)
        conn.dialogue.put(Message(role='user', content=query))
        raw = ''.join(reply.response(conn, None, depth))
        checked = conn._mia_persona.checked_text(raw)
        conn.dialogue.put(Message(role='assistant', content=checked))
        return raw, checked

    async def connection(socket):
        headers = dict(socket.request.headers)
        assert transport.verify_token(headers.get('authorization', '')[7:], headers.get('client-id'), headers.get('device-id'))
        conn = SimpleNamespace(config=configuration, headers=headers, websocket=socket, read_config_from_api=True,
            need_bind=False, dialogue=Dialogue(), session_id=str(uuid.uuid4()), sentence_id=None,
            loop=asyncio.get_running_loop(), client_abort=False, tts=SimpleNamespace(tts_text_queue=Queue()))
        llm = None
        try:
            private = await load_private_config(conn)
            scope = conn._mia_scope
            module = private['selected_module']['LLM']
            model = private['LLM'][module]
            llm = conn.llm = selected_provider(model, report, 'reply')
            profile = ROOT / 'context-profile.json'
            profile.write_text(json.dumps({'provider_module': type(llm).__module__, 'model': llm.model_name,
                'base_url': llm.base_url, 'context_window': 8192,
                'capacity_source': 'Isolated short-request CI envelope; not verified production capacity'}))
            os.environ['MIA_CONTEXT_PROFILE_FILE'] = str(profile)
            conn._mia_context_builder = ContextBuilder(index)
            conn._mia_memory = adapter.MiaMemoryProvider(store, scope.owner, llm, conn.session_id, scope, auth)
            conn.prompt = private['prompt']
            conn.change_system_prompt = lambda text: conn.dialogue.update_system_message(adapter.compose_persona(conn, text))
            adapter.compose_persona(conn, private['prompt'])
            adapter.attach_output_guard(conn)

            jobs = worker.jobs
            conn.server = runtime
            await socket.send(json.dumps({'type': 'hello', 'session_id': conn.session_id, 'pid': os.getpid()}))
            async for message in socket:
                if await adapter.handle_message(conn, message):
                    continue
                request = json.loads(message)
                assert request['type'] == 'test_chat' and isinstance(request['query'], str)
                conn.sentence_id = str(uuid.uuid4())
                raw, checked = await asyncio.to_thread(chat, conn, request['query'])
                turn = conn._mia_context_turn
                diagnostics = turn.bundle.diagnostics()
                case = {'query': request['query'], 'raw': raw, 'delivered': checked, 'diagnostics': diagnostics,
                    'session_id': conn.session_id, 'pid': os.getpid(), 'input': turn.bundle.request()}
                with LOCK:
                    report['cases'].append(case)
                    save(report)
                await socket.send(json.dumps({'type': 'test_reply', **case}))
                # Foreground reply is sent BEFORE extraction; actual completion
                # admission/Worker, not a hand-built memory insertion.
                deadline = time.monotonic() + 65
                while True:
                    status = await asyncio.to_thread(jobs.current, conn._mia_job_status)
                    if status['state'] in {'committed', 'empty', 'failed', 'cancelled'}:
                        break
                    assert time.monotonic() < deadline, 'Accepted Worker task did not terminate in time'
                    await asyncio.sleep(.1)
                assert status['state'] in {'committed', 'empty'}, 'Actual extraction did not reach a valid terminal state'
                await socket.send(json.dumps({'type': 'test_saved', 'job_state': status['state'],
                    'memories': store.list_memories(scope.owner), 'events': store.handle(scope.owner, {'action': 'events'})['events']}))
        except PrivateAuthorizationRequired:
            await socket.send(json.dumps({'type': 'mia_authorization', 'status': 'required'}))
        except Exception as error:
            with LOCK:
                report['service_error_class'] = type(error).__name__
                report['service_error_locations'] = [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                    for frame in traceback.extract_tb(error.__traceback__)[-8:]]
                save(report)
            await socket.send(json.dumps({'type': 'test_error', 'error_class': type(error).__name__}))
        finally:
            if llm:
                llm.client.close()

    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(os.environ['MIA_TLS_CERT_FILE'], os.environ['MIA_TLS_KEY_FILE'])
    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    try:
        async with wss(connection, '127.0.0.1', 0, ssl=tls) as server:
            ready = ROOT / 'ready.tmp'
            ready.write_text(json.dumps({'port': server.sockets[0].getsockname()[1], 'pid': os.getpid()}))
            ready.replace(ROOT / 'ready.json')
            await stop.wait()
    finally:
        await adapter.stop_worker(runtime)
        store.close()


async def drive():
    from websockets.asyncio.client import connect
    fixture_path = Path(__file__).resolve().parents[2] / 'server/tests/fixtures/persona_memory_behavior_p22_v1.json'
    dataset = json.loads(fixture_path.read_text())
    sample = dataset['rounds'][int(os.environ['MIA_BEHAVIOR_ROUND'])]
    report = {'code_sha': os.environ['GITHUB_SHA'], 'round': int(os.environ['MIA_BEHAVIOR_ROUND']),
        'dataset_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(), 'requests': 0, 'request_kinds': [],
        'cases': [], 'extraction_outputs': [], 'passed': False, 'server_pids': [],
        'scope': 'Actual manager TLS authorization, WSS bridge restart, existing Provider SDK, BGE and SQLite; synthetic users; audio consumers omitted',
        'limits': {'requests_per_round': 18, 'rounds': 3, 'http_timeout_seconds': 30, 'sdk_retries': 0, 'worker_maximum_attempts': 2, 'output_tokens': 768},
        'B01_B03_B04_B06_B08': 'not_accepted_by_this_gate', 'B07': 'real-calendar acceptance delegated to user',
        'background_lifecycle': 'installed start_worker/stop_worker; no manual task pumping',
        'production_capacity': 'unverified; isolated short-request envelope only',
        'configured_model': os.environ['MIA_TEST_LLM_MODEL'],
        'embedding': {'model_id': reply._encoder.model_id, 'revision': reply._encoder.revision, 'dimension': reply._encoder.dimension}}
    save(report)
    transport = AuthManager('synthetic-behavior-transport')
    device, client = os.environ['MIA_SCOPE_DEVICE'], os.environ['MIA_SCOPE_CLIENT']
    headers = {'device-id': device, 'client-id': client,
        'authorization': 'Bearer ' + transport.generate_token(client, device),
        'mia-private-credential': os.environ['MIA_SCOPE_CREDENTIAL']}
    tls = ssl.create_default_context(cafile=os.environ['MIA_SCOPE_CA'])
    process = None
    endpoint = None
    phase = 'service_start'

    async def start():
        nonlocal process, endpoint
        ready = ROOT / 'ready.json'
        ready.unlink(missing_ok=True)
        with (ROOT / 'service.log').open('ab') as output:
            process = subprocess.Popen([sys.executable, __file__, '--serve'], stdout=output, stderr=output)
        deadline = time.monotonic() + 45
        while not ready.exists():
            assert process.poll() is None and time.monotonic() < deadline, 'WSS service did not start'
            await asyncio.sleep(.1)
        state = json.loads(ready.read_text())
        endpoint = 'wss://127.0.0.1:' + str(state['port'])
        return state['pid']

    async def stop():
        nonlocal process
        if process and process.poll() is None:
            process.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=25)
            except asyncio.TimeoutError:
                process.kill()
                await asyncio.to_thread(process.wait)
                raise AssertionError('WSS service exceeded bounded shutdown')
            assert process.returncode == 0, 'WSS service did not shut down cleanly'

    async def ask(query):
        async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            hello = json.loads(await socket.recv())
            assert hello['type'] == 'hello'
            await socket.send(json.dumps({'type': 'test_chat', 'query': query}))
            answer = None
            while True:
                value = json.loads(await asyncio.wait_for(socket.recv(), timeout=65))
                assert value['type'] not in {'test_error', 'mia_authorization'}
                if value['type'] == 'test_reply':
                    answer = value
                    assert not PersonaGuardrail().inspect_output(value['raw'])[1]
                if value['type'] == 'test_saved':
                    assert answer is not None
                    return answer, value

    async def manage(action, **fields):
        async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            assert json.loads(await socket.recv())['type'] == 'hello'
            marker = str(uuid.uuid4())
            await socket.send(json.dumps({'type': 'mia_memory', 'request_id': marker, 'action': action, **fields}))
            value = json.loads(await socket.recv())
            assert value['request_id'] == marker and 'error' not in value
            return value['result']

    try:
        first_pid = await start()
        phase = 'source_completion_and_extraction'
        _, saved = await ask(sample['source'])
        introduced = saved['memories']
        facts = [row for row in introduced if row['confirmed']]
        assert facts and all(row['source'] for row in facts), 'Actual source was not saved with evidence'
        fact_ids = {row['id'] for row in facts}
        phase = 'new_session_paraphrase_recall'
        answer, _ = await ask(sample['recall'])
        assert fact_ids.intersection(answer['diagnostics']['selected_fact_ids'])
        actual_input = json.dumps(answer['input'], ensure_ascii=False)
        assert all(any(word in actual_input for word in group) for group in sample['answer_groups'])
        assert all(any(word in answer['raw'] for word in group) for group in sample['answer_groups'])
        phase = 'event_activation'
        continued, saved = await ask(sample['continuity'])
        assert fact_ids.intersection(continued['diagnostics']['selected_fact_ids'])
        active = [event for event in saved['events'] if event['event_type'] == 'continuity' and event['state'] == 'active']
        assert len(active) == 1
        phase = 'actual_service_restart'
        await stop()
        second_pid = await start()
        assert first_pid != second_pid
        phase = 'event_restoration_and_repeat'
        repeated, saved = await ask(sample['repeat'])
        assert repeated['session_id'] != continued['session_id']
        assert [event['id'] for event in saved['events'] if event['event_type'] == 'continuity' and event['state'] == 'active'] == [active[0]['id']]
        again, saved = await ask(sample['repeat_again'])
        assert again['session_id'] != repeated['session_id']
        assert [event['id'] for event in saved['events'] if event['event_type'] == 'continuity' and event['state'] == 'active'] == [active[0]['id']]
        phase = 'source_deletion_and_unknown'
        for row in introduced:
            await manage('delete', id=row['id'])
        unknown, saved = await ask(sample['unknown'])
        assert not unknown['diagnostics']['selected_fact_ids'] and not saved['memories']
        assert re.search(r'不知道|不清楚|没有.{0,12}(?:信息|记录)|还看不出|不记得|无法.{0,8}(?:确定|判断)', unknown['raw'])
        assert all(event['state'] != 'active' for event in saved['events'])
        report = json.loads(REPORT.read_text())
        report.update(passed=True, server_pids=[first_pid, second_pid], genuine_wss_restart=True,
            followup_sessions_after_event=3, actual_extraction_and_real_bge=True, deletion_removed_recall_and_event=True,
            raw_response_review='required; automated gates alone do not establish full semantic acceptance')
    except Exception as error:
        report = json.loads(REPORT.read_text())
        report.update(passed=False, error_class=type(error).__name__, failed_phase=phase,
            error_locations=[{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                for frame in traceback.extract_tb(error.__traceback__)[-8:]])
    finally:
        try:
            await stop()
        except Exception as error:
            report.update(passed=False, shutdown_error_class=type(error).__name__)
        decision_keys = {'passed', 'error_class', 'failed_phase', 'error_locations', 'server_pids', 'genuine_wss_restart',
            'followup_sessions_after_event', 'actual_extraction_and_real_bge', 'deletion_removed_recall_and_event',
            'raw_response_review', 'shutdown_error_class'}
        decision = {key: report[key] for key in decision_keys if key in report}
        # Shutdown may finish an in-flight real request. Keep its final output
        # and count rather than overwriting it with a pre-shutdown snapshot.
        report = json.loads(REPORT.read_text())
        report.update(decision)
        save(report)
    print(json.dumps({'behavior_round': report['round'], 'passed': report['passed'], 'requests': report['requests']}))
    if not report['passed']:
        raise SystemExit('Real composed behavior gate failed; inspect sanitized report')


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    asyncio.run(serve() if '--serve' in sys.argv else drive())
