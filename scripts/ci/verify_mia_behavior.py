"""First P22 composed real-manager/BGE/provider gate; other B01-B08 gates remain explicit.

Only synthetic CI users. The WSS harness drives the installed reply/completion
bridge; it omits microphone/TTS consumers, not model or embedding responses.
"""

import __future__
import ast
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
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from plugins_func.register import Action, ActionResponse
from mia_companion.authorization import PrivateAuthorizationRequired, load_private_config
from mia_companion.context import ContextBuilder
from mia_companion.persona import PersonaGuardrail
from mia_companion.semantic import SemanticMemoryIndex
from mia_companion import authorization, reply, xiaozhi_adapter as adapter


ROOT = Path(os.environ['MIA_BEHAVIOR_DIR']) / ('round-' + os.environ['MIA_BEHAVIOR_ROUND'])
REPORT = ROOT / 'results.json'
LOCK = threading.Lock()
SUITE = os.environ.get('MIA_BEHAVIOR_SUITE', 'continuity')
assert SUITE in {'continuity', 'tools', 'correction', 'natural_correction', 'retrieval', 'retrieval_holdout', 'inflight', 'recovery'}
REQUEST_CAP = 48 if SUITE == 'tools' else 20


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
            assert report['requests'] < REQUEST_CAP, 'Per-round real request budget exhausted'
            report['requests'] += 1
            report['request_kinds'].append(purpose)
            if purpose == 'reply':
                request = json.loads(json.dumps({key: kwargs[key] for key in ('messages', 'tools', 'max_tokens') if key in kwargs}))
                turn = getattr(provider._mia_connection, '_mia_context_turn', None)
                request['diagnostics'] = turn.bundle.diagnostics() if turn else None
                provider._mia_requests.append(request)
                report.setdefault('sdk_requests', []).append(request)
            save(report)
        return create(*args, **kwargs)

    provider.client.chat.completions.create = counted
    if purpose == 'reply':
        response = provider.response
        provider._mia_raw_chunks = []
        provider._mia_requests = []

        def streamed(*args, **kwargs):
            provider._mia_raw_chunks.clear()
            for value in response(*args, **kwargs):
                provider._mia_raw_chunks.append(value)
                yield value

        provider.response = streamed
        function_response = provider.response_with_functions

        def function_streamed(*args, **kwargs):
            provider._mia_raw_chunks.clear()
            for content, calls in function_response(*args, **kwargs):
                if content:
                    provider._mia_raw_chunks.append(content)
                if calls:
                    # Preserve the real SDK deltas before ConnectionHandler
                    # merges them; do not infer parallel output from inputs.
                    with LOCK:
                        provider._mia_requests[-1].setdefault('tool_call_deltas', []).append(
                            [call.model_dump(exclude_none=True) for call in calls])
                        save(report)
                yield content, calls

        provider.response_with_functions = function_streamed
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


def installed_connection(report):
    # Same AST-loading approach as verify_mia_reply: preserve the installed
    # ConnectionHandler bodies and decorators, omitting audio/plugin imports.
    path = Path('core/connection.py')
    source = path.read_text()
    tree = ast.parse(source)
    names = {'ConnectionHandler', 'DIRECT_ANSWER_TOOL'}
    selected = [node for node in tree.body if getattr(node, 'name', None) in names
        or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)]
    assert len(selected) == len(names)
    namespace = dict(asyncio=asyncio, json=json, re=re, uuid=uuid, time=time, TAG='P22', mia=adapter, mia_auth=authorization,
        Message=Message, Dialogue=Dialogue, TTSMessageDTO=TTSMessageDTO, SentenceType=SentenceType,
        ContentType=ContentType, Action=Action, ActionResponse=ActionResponse,
        enqueue_tool_report=lambda *args, **kwargs: None,
        get_system_error_response=lambda config: 'UNEXPECTED_UPSTREAM_ERROR')
    utility = ast.parse(Path('core/utils/util.py').read_text())
    extractors = [node for node in utility.body if getattr(node, 'name', None) == 'extract_json_from_string']
    assert len(extractors) == 1
    exec(compile(ast.Module(body=extractors, type_ignores=[]), 'core/utils/util.py', 'exec'), namespace)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec',
        flags=__future__.annotations.compiler_flag), namespace)
    report['installed_connection_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    report['connection_scope'] = 'Installed ConnectionHandler.chat bodies/decorators; constructed without audio initialization; not full WebSocketServer lifecycle'
    save(report)
    return namespace['ConnectionHandler']


async def serve():
    from websockets.asyncio.server import serve as wss
    report = json.loads(REPORT.read_text())

    def upstream_error(*args, **kwargs):
        with LOCK:
            report.setdefault('upstream_errors', []).append(str(args[0])[:1000] if args else 'error')
            report['upstream_errors'] = report['upstream_errors'][-10:]
            save(report)

    logger.error = upstream_error
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
    recovery_control = {}
    if SUITE == 'recovery':
        from mia_behavior_recovery import observe_commit
        observe_commit(worker, recovery_control, ROOT, report, LOCK, save)
    index = SemanticMemoryIndex(store, reply._encoder)
    if SUITE in {'retrieval', 'retrieval_holdout'}:
        actual_retrieve = index.retrieve

        async def observed_retrieve(*args, **kwargs):
            value = await actual_retrieve(*args, **kwargs)
            with LOCK:
                report.setdefault('retrievals', []).append(json.loads(json.dumps(value)))
                save(report)
            return value

        index.retrieve = observed_retrieve
    transport = AuthManager('synthetic-behavior-transport')
    handler = installed_connection(report)
    tools_fixture = (json.loads((Path(__file__).resolve().parents[2] /
        'server/tests/fixtures/persona_memory_tools_p22_v1.json').read_text()) if SUITE == 'tools' else None)
    held_extraction = {}
    if SUITE == 'inflight':
        from mia_behavior_inflight import observe_worker
        correction_fixture = json.loads((Path(__file__).resolve().parents[2] /
            'server/tests/fixtures/persona_memory_correction_p22_v1.json').read_text())
        hold_query = '请记住' + correction_fixture['rounds'][int(os.environ['MIA_BEHAVIOR_ROUND'])]['replacement']
        observe_worker(worker, held_extraction, ROOT, report, LOCK, save)

    class TextSink:
        def __init__(self):
            self.tts_text_queue = Queue()

        def store_tts_text(self, sentence_id, text):
            pass

        def tts_one_sentence(self, active, content_type, content_detail):
            self.tts_text_queue.put(TTSMessageDTO(active.sentence_id, SentenceType.MIDDLE, content_type, content_detail))

    async def connection(socket):
        headers = dict(socket.request.headers)
        assert transport.verify_token(headers.get('authorization', '')[7:], headers.get('client-id'), headers.get('device-id'))
        conn = object.__new__(handler)
        conn.__dict__.update(config=configuration, headers=headers, websocket=socket, read_config_from_api=True,
            need_bind=False, dialogue=Dialogue(), session_id=str(uuid.uuid4()), sentence_id=None,
            loop=asyncio.get_running_loop(), client_abort=False, tts=TextSink(), logger=logger,
            intent_type='nointent', current_speaker=None, system_introduced_speakers=set(), features={'emoji': False})
        llm = None
        specification = None
        try:
            private = await load_private_config(conn)
            scope, auth = conn._mia_scope, conn._mia_authorization
            module = private['selected_module']['LLM']
            model = private['LLM'][module]
            llm = conn.llm = selected_provider(model, report, 'reply')
            llm._mia_connection = conn
            profile = ROOT / 'context-profile.json'
            profile.write_text(json.dumps({'provider_module': type(llm).__module__, 'model': llm.model_name,
                'base_url': llm.base_url, 'context_window': 8192,
                'capacity_source': 'Isolated short-request CI envelope; not verified production capacity'}))
            os.environ['MIA_CONTEXT_PROFILE_FILE'] = str(profile)
            conn._mia_context_builder = ContextBuilder(index)
            conn.memory = None
            conn._initialize_memory()
            assert conn._mia_memory.store is store and conn._mia_memory.authorization is auth
            conn.change_system_prompt(private['prompt'])
            adapter.attach_output_guard(conn)

            jobs = worker.jobs
            conn.server = runtime
            await socket.send(json.dumps({'type': 'hello', 'session_id': conn.session_id, 'pid': os.getpid()}))
            async for message in socket:
                if await adapter.handle_message(conn, message):
                    continue
                request = json.loads(message)
                assert request['type'] == 'test_chat' and isinstance(request['query'], str)
                if request.get('hold_commit'):
                    assert SUITE == 'recovery' and not recovery_control
                    fixture = json.loads((Path(__file__).resolve().parents[2] /
                        'server/tests/fixtures/persona_memory_recovery_p22_v1.json').read_text())
                    assert request['query'] == fixture['rounds'][int(os.environ['MIA_BEHAVIOR_ROUND'])]['source']
                    await authorization.require_connection(conn, 'memory:write')
                    recovery_control.update(owner=scope.owner, source=request['query'])
                if request.get('hold_extraction'):
                    assert SUITE == 'inflight' and request['query'] == hold_query and not held_extraction
                    await authorization.require_connection(conn, 'memory:write')
                    held_extraction.update(owner=scope.owner, source=request['query'])
                specification = None
                calls, hashes, fault = [], {}, {}
                if request.get('tool_case_id'):
                    assert tools_fixture is not None
                    specification = next(row for row in tools_fixture['cases'] if row['id'] == request['tool_case_id'])
                    assert request['query'] == specification['query']
                    from mia_behavior_tools import attach_tools

                    def record_call(item):
                        with LOCK:
                            report.setdefault('tool_calls', []).append(dict(item))
                            save(report)

                    async def before_result(active, item):
                        if not specification.get('fault') or fault:
                            return
                        fault.update(applied=True, reply_requests=len(llm._mia_requests))
                        if specification['outcome'] == 'context_changed':
                            await authorization.require_connection(active, 'memory:manage')
                            targets = store.list_memories(scope.owner)
                            assert targets, 'No genuine source remains for deletion fault'
                            for target in targets:
                                await adapter.handle_message(active, json.dumps({'type': 'mia_memory',
                                    'request_id': str(uuid.uuid4()), 'action': 'delete', 'id': target['id']}))
                        else:
                            assert specification['outcome'] == 'authorization_required'
                            async with httpx.AsyncClient(timeout=5, trust_env=False,
                                    verify=ssl.create_default_context(cafile=os.environ['MIA_SCOPE_CA'])) as http:
                                result = await http.post(os.environ['MIA_SCOPE_MANAGER_URL'].rstrip('/') + '/device/mia-auth/revoke',
                                    json={'device_id': scope.device_id},
                                    headers={'Authorization': 'Bearer ' + os.environ['MIA_SCOPE_USER_TOKEN']})
                                assert result.json()['code'] == 0

                    calls, hashes = attach_tools(conn, tools_fixture,
                        tools_fixture['rounds'][int(os.environ['MIA_BEHAVIOR_ROUND'])], specification,
                        record_call=record_call, before_result=before_result)
                    if specification.get('history_fixture'):
                        assert conn._mia_context_turn is not None, 'Long-history case requires actual warmup turn'
                        history = specification['history_fixture']
                        for number in range(history['turns']):
                            conn.dialogue.put(Message(role='user', content=f'CONTEXT_FIXTURE_{number}:' + '旧话题' * (history['characters_per_user_message'] // 3)))
                            conn.dialogue.put(Message(role='assistant', content='合成历史上下文片段，不是实际模型的旧回复。'))
                with store.lock:
                    jobs_before = store.db.execute('SELECT COUNT(*) FROM mia_jobs WHERE owner=?', (scope.owner,)).fetchone()[0]
                conn.sentence_id = str(uuid.uuid4())
                llm._mia_requests.clear()
                retrieval_start = len(report.get('retrievals', []))
                completed = await asyncio.to_thread(conn.chat, request['query'])
                if specification is None:
                    assert completed is True, 'Installed chat did not complete'
                raw = ''.join(llm._mia_raw_chunks)
                checked = conn.dialogue.dialogue[-1].content if conn.dialogue.dialogue[-1].role == 'assistant' else ''
                spoken = []
                while not conn.tts.tts_text_queue.empty():
                    item = conn.tts.tts_text_queue.get_nowait()
                    if item.content_type == ContentType.TEXT:
                        spoken.append(item.content_detail)
                turn = conn._mia_context_turn
                last_request = llm._mia_requests[-1] if llm._mia_requests else {}
                diagnostics = turn.bundle.diagnostics() if turn else last_request.get('diagnostics')
                with store.lock:
                    jobs_after = store.db.execute('SELECT COUNT(*) FROM mia_jobs WHERE owner=?', (scope.owner,)).fetchone()[0]
                case = {'query': request['query'], 'raw': raw, 'delivered': checked, 'tts_text': ''.join(spoken), 'diagnostics': diagnostics,
                    'session_id': conn.session_id, 'pid': os.getpid(),
                    'input': turn.bundle.request() if turn else {key: last_request[key] for key in ('messages', 'tools', 'max_tokens') if key in last_request},
                    'tool_case_id': specification['id'] if specification else None, 'tool_calls': calls,
                    'installed_tool_sources': hashes, 'sdk_requests': list(llm._mia_requests),
                    'retrievals': list(report.get('retrievals', [])[retrieval_start:]),
                    'context_status': conn._mia_context_status, 'fault': fault,
                    'job_delta': jobs_after - jobs_before, 'admission_status': dict(conn._mia_job_status or {}),
                    'history_fixture': specification.get('history_fixture') if specification else None}
                with LOCK:
                    report['cases'].append(case)
                    save(report)
                # Never send pre-revocation private inputs/diagnostics back to
                # an unauthorized peer. Full internal CI traces stay in the
                # sanitized server artifact, not in this denial frame.
                try:
                    await authorization.require_connection(conn)
                except PrivateAuthorizationRequired:
                    await socket.send(json.dumps({'type': 'test_denied', 'fault_applied': bool(fault),
                        'job_delta': case['job_delta'], 'reply_requests': len(llm._mia_requests),
                        'reply_requests_at_fault': fault.get('reply_requests'),
                        'tool_records': [item['record_id'] for item in calls]}))
                    continue
                if specification and case['context_status'].get('status') == 'limited':
                    await socket.send(json.dumps({'type': 'test_limited', 'context_status': case['context_status'],
                        'tool_calls': calls, 'job_delta': case['job_delta'], 'admitted': conn._mia_job_status is not None,
                        'reply_requests': len(llm._mia_requests), 'reply_requests_at_fault': fault.get('reply_requests')}))
                    continue
                if specification and specification['outcome'] == 'context_changed' and fault:
                    # P15 rebuilds from current evidence without old tool data;
                    # it does not require an immediate limited-context reply.
                    from mia_companion.persona import CORE
                    initial, rebuilt = llm._mia_requests[0], last_request
                    original_data = json.loads(initial['messages'][1]['content'])['mia_context']
                    removed = original_data['facts']
                    rebuilt_data = json.loads(rebuilt['messages'][1]['content'])['mia_context']
                    serialized = json.dumps(rebuilt['messages'], ensure_ascii=False)
                    checks = {
                        'initial_facts_present': bool(removed),
                        'facts_removed': not rebuilt_data['facts'] and not rebuilt['diagnostics']['selected_fact_ids'],
                        'old_quotes_removed': all(row['content'] not in serialized for row in removed),
                        'tools_removed': not rebuilt.get('tools'),
                        'old_tool_chain_removed': all(row['role'] != 'tool' and not row.get('tool_calls')
                            for row in rebuilt['messages']),
                        'core_preserved': rebuilt['messages'][0]['content'].startswith(CORE),
                        'question_preserved': rebuilt['messages'][-1] == {'role': 'user', 'content': request['query']},
                        'budget_valid': rebuilt['diagnostics']['estimated_input'] <= rebuilt['diagnostics']['input_limit'],
                    }
                    await socket.send(json.dumps({'type': 'test_replanned', 'rebuild_checks': checks,
                        'fault_applied': bool(fault), 'job_delta': case['job_delta'],
                        'admission_status': case['admission_status'], 'reply_requests': len(llm._mia_requests),
                        'reply_requests_at_fault': fault.get('reply_requests'),
                        'tool_records': [item['record_id'] for item in calls]}))
                    continue
                assert spoken, 'Installed chat delivered no guarded TTS text'
                await socket.send(json.dumps({'type': 'test_reply', **case}))
                # Foreground reply is sent BEFORE extraction; actual completion
                # admission/Worker, not a hand-built memory insertion.
                assert conn._mia_job_status and conn._mia_job_status.get('id'), 'Completed turn was not admitted'
                deadline = time.monotonic() + 65
                while True:
                    status = await asyncio.to_thread(jobs.current, conn._mia_job_status)
                    if status['state'] in {'committed', 'empty', 'failed', 'cancelled'}:
                        break
                    assert time.monotonic() < deadline, 'Accepted Worker task did not terminate in time'
                    await asyncio.sleep(.1)
                if request.get('hold_extraction') and status['state'] == 'cancelled':
                    await authorization.require_connection(conn)
                    await socket.send(json.dumps({'type': 'test_cancelled', 'job_id': status['id'], 'state': status['state']}))
                    continue
                assert status['state'] in {'committed', 'empty'}, 'Actual extraction did not reach a valid terminal state'
                await authorization.require_connection(conn)
                await socket.send(json.dumps({'type': 'test_saved', 'job_state': status['state'],
                    'memories': store.list_memories(scope.owner), 'events': store.handle(scope.owner, {'action': 'events'})['events']}))
        except PrivateAuthorizationRequired:
            await socket.send(json.dumps({'type': 'mia_authorization', 'status': 'required'}))
        except Exception as error:
            with LOCK:
                report.setdefault('service_errors', []).append({'case_id': specification['id'] if specification else None,
                    'error_class': type(error).__name__, 'admission_status': dict(getattr(conn, '_mia_job_status', None) or {})})
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
    fixture_name = {'tools': 'persona_memory_tools_p22_v1.json',
        'correction': 'persona_memory_correction_p22_v1.json',
        'natural_correction': 'persona_memory_natural_correction_p22_v1.json',
        'retrieval': 'persona_memory_retrieval_p22_v1.json',
        'retrieval_holdout': 'persona_memory_retrieval_p22_v2.json',
        'recovery': 'persona_memory_recovery_p22_v1.json',
        'inflight': 'persona_memory_correction_p22_v1.json',
        'continuity': 'persona_memory_behavior_p22_v1.json'}[SUITE]
    fixture_path = Path(__file__).resolve().parents[2] / 'server/tests/fixtures' / fixture_name
    dataset = json.loads(fixture_path.read_text())
    sample = dataset['rounds'][int(os.environ['MIA_BEHAVIOR_ROUND'])]
    report = {'code_sha': os.environ['GITHUB_SHA'], 'suite': SUITE, 'round': int(os.environ['MIA_BEHAVIOR_ROUND']),
        'dataset_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(), 'requests': 0, 'request_kinds': [],
        'cases': [], 'extraction_outputs': [], 'passed': False, 'server_pids': [],
        'scope': 'Actual manager TLS authorization, WSS bridge restart, existing Provider SDK, BGE and SQLite; synthetic users; audio consumers omitted',
        'limits': {'requests_per_round': REQUEST_CAP, 'rounds': 3, 'http_timeout_seconds': 30, 'sdk_retries': 0, 'worker_maximum_attempts': 2, 'output_tokens': 768},
        'B01_B03_B04_B06_B08': 'not_accepted_by_this_gate', 'B07': 'real-calendar acceptance delegated to user',
        'background_lifecycle': 'installed start_worker/stop_worker; no manual task pumping',
        'persona_reference': 'insistgang/Luyao_AI_Project@e23c3aa25d6451e3f35e71609864bb3a54ad49a0; user requested no additional expression gate',
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

    async def ask(query, tool_case=None):
        async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            hello = json.loads(await socket.recv())
            assert hello['type'] == 'hello'
            async def exchange(text, specification=None):
                await socket.send(json.dumps({'type': 'test_chat', 'query': text,
                    'tool_case_id': specification['id'] if specification else None}))
                answer = None
                while True:
                    value = json.loads(await asyncio.wait_for(socket.recv(), timeout=65))
                    assert value['type'] != 'test_error'
                    if value['type'] == 'mia_authorization':
                        assert specification and specification['outcome'] == 'authorization_required'
                    if value['type'] in {'test_denied', 'test_limited', 'test_replanned'}:
                        assert specification is not None
                        return value, None
                    if value['type'] == 'test_reply':
                        answer = value
                        assert not PersonaGuardrail().inspect_output(value['raw'])[1]
                    if value['type'] == 'test_saved':
                        assert answer is not None
                        return answer, value
            if tool_case and tool_case.get('history_fixture'):
                await exchange('你好。')
            return await exchange(query, tool_case)

    async def manage(action, expect_denial=False, **fields):
        async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            first = json.loads(await socket.recv())
            if expect_denial:
                assert first['type'] == 'mia_authorization' and first['status'] == 'required'
                return first
            assert first['type'] == 'hello'
            marker = str(uuid.uuid4())
            await socket.send(json.dumps({'type': 'mia_memory', 'request_id': marker, 'action': action, **fields}))
            value = json.loads(await socket.recv())
            assert value['request_id'] == marker and 'error' not in value
            return value['result']

    try:
        first_pid = await start()
        if SUITE == 'tools':
            phase = 'ten_real_tool_and_context_scenarios'
            from mia_behavior_tools import drive_tools
            results = await drive_tools(dataset, sample, ask, manage)
            report = json.loads(REPORT.read_text())
            report.update(passed=all(row['structural_pass'] for row in results), server_pids=[first_pid],
                tool_results=results, B08_semantic_acceptance='pending raw-response review of all thirty cases',
                raw_response_review='required; structural checks alone do not establish >=90% semantic accuracy')
        elif SUITE == 'recovery':
            phase = 'real_database_failure_and_crash'
            from mia_behavior_recovery import fail_commit_and_crash

            async def crash():
                assert process.poll() is None
                process.kill()
                await asyncio.to_thread(process.wait)
                assert process.returncode == -signal.SIGKILL

            proof = await fail_commit_and_crash(endpoint, tls, headers, ROOT, sample['source'], crash)
            assert proof['ready']['pid'] == first_pid
            phase = 'validated_result_restart_without_reextraction'
            second_pid = await start()
            assert second_pid != first_pid
            deadline = time.monotonic() + 65
            while True:
                status = await manage('job_status', id=proof['ready']['job_id'])
                if status['state'] == 'committed':
                    break
                assert status['state'] == 'validated' and time.monotonic() < deadline
                await asyncio.sleep(.1)
            resumed = json.loads(REPORT.read_text())
            assert resumed['requests'] == proof['ready']['requests']
            assert len(resumed['extraction_outputs']) == proof['ready']['extraction_outputs']
            assert len(resumed.get('recovery_resolves', [])) == proof['ready']['resolve_calls']
            assert status['attempts'] == proof['ready']['attempts']
            facts = (await manage('list'))['memories']
            assert len(facts) == 1 and facts[0]['content'] == sample['source'] and facts[0]['source']
            proof.update(recovered_state=status['state'], attempts=status['attempts'],
                no_model_or_resolver_repeat=True, recovered_fact_id=facts[0]['id'])
            phase = 'recovered_fact_new_session_recall'
            answer, saved = await ask(sample['query'])
            assert answer['session_id'] != proof['source_session_id']
            assert facts[0]['id'] in answer['diagnostics']['selected_fact_ids']
            assert len(saved['memories']) == 1
            proof.update(recall_response=answer['tts_text'], expected_terms=sample['answer_terms'])
            report = json.loads(REPORT.read_text())
            report.update(passed=True, server_pids=[first_pid, second_pid], genuine_wss_restart=True,
                recovery_proof=proof, raw_response_review='required; real SQLite failure and recovery only, not full B03')
        elif SUITE in {'retrieval', 'retrieval_holdout'}:
            phase = 'actual_source_generated_four_component_retrieval'
            from mia_behavior_retrieval import drive_retrieval
            analysis = await drive_retrieval(sample, ask)
            report = json.loads(REPORT.read_text())
            report.update(passed=all(row['structural_pass'] for row in analysis['cases'])
                and analysis['all_components_observed'], retrieval_analysis=analysis, server_pids=[first_pid],
                raw_response_review='required; actual source metadata and answer ownership, not only nonzero scores')
        elif SUITE in {'correction', 'natural_correction', 'inflight'}:
            phase = 'correction_original_source'
            original, saved = await ask(sample['source'])
            facts = [row for row in saved['memories'] if row['confirmed'] and row['content'] == sample['source']]
            assert len(facts) == 1 and facts[0]['source']
            target = facts[0]['id']
            phase = 'correction_original_interaction'
            previous, saved = await ask('你还记得' + sample['source'] + '吗？')
            assert target in previous['diagnostics']['selected_fact_ids']
            old_events = {row['id'] for row in saved['events'] if row['state'] == 'active'}
            assert old_events, 'Original interaction did not create a genuine active event'
            phase = 'correction_actual_worker_reconciliation'
            correction_query = (sample['replacement'] if SUITE == 'natural_correction'
                else '更正：' + sample['source'] + '；' + sample['replacement'])
            corrected, saved = await ask(correction_query)
            current = [row for row in saved['memories'] if row['id'] == target]
            assert len(current) == 1 and current[0]['confirmed'] and current[0]['content'] == sample['replacement']
            assert not old_events.intersection(row['id'] for row in saved['events'] if row['state'] == 'active')
            phase = 'correction_restart_and_third_wording'
            await stop()
            second_pid = await start()
            assert first_pid != second_pid
            recalled, saved = await ask(sample['query'])
            assert target in recalled['diagnostics']['selected_fact_ids']
            facts = json.loads(recalled['input']['messages'][1]['content'])['mia_context']['facts']
            assert any(row['id'] == target and row['content'] == sample['replacement'] for row in facts)
            assert all(row['content'] != sample['source'] for row in facts)
            assert any(word in recalled['tts_text'] for word in sample['answer_words'])
            assert len({original['session_id'], previous['session_id'], corrected['session_id'], recalled['session_id']}) == 4
            phase = 'correction_delete_and_restart'
            inflight_proof = None
            if SUITE == 'inflight':
                assert len(saved['memories']) == 1 and saved['memories'][0]['id'] == target
                phase = 'delete_while_genuine_validated_extraction_is_in_flight'
                from mia_behavior_inflight import delete_while_extraction_held
                inflight_proof = await delete_while_extraction_held(endpoint, tls, headers, ROOT,
                    '请记住' + sample['replacement'], target, manage)
            else:
                for row in saved['memories']:
                    await manage('delete', id=row['id'])
            assert not (await manage('list'))['memories']
            await stop()
            third_pid = await start()
            assert len({first_pid, second_pid, third_pid}) == 3
            after_delete, saved = await ask(sample['query'])
            assert not after_delete['diagnostics']['selected_fact_ids'] and not saved['memories']
            assert all(row['state'] != 'active' for row in saved['events'])
            report = json.loads(REPORT.read_text())
            report.update(passed=True, server_pids=[first_pid, second_pid, third_pid], genuine_wss_restart=True,
                correction_original_id=target, correction_current_fact=sample['replacement'],
                correction_deleted_after_restart=True, correction_old_events=sorted(old_events),
                inflight_proof=inflight_proof,
                raw_response_review='required; this selected correction corpus and optional held-result deletion only, not arbitrary natural correction/growth/trend/identity acceptance')
        else:
            phase = 'persona_identity'
            identity, saved = await ask('你是谁？')
            assert re.search(r'Mia|米娅', identity['tts_text'], re.I)
            assert not saved['memories'], 'Identity question introduced private facts'
            phase = 'persona_companionship'
            _, saved = await ask('我今天有点累，想和你待一会儿。')
            assert not saved['memories'], 'Transient companionship request became a durable private fact'
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
            assert all(any(word in answer['tts_text'] for word in group) for group in sample['answer_groups'])
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
            later, saved = await ask(sample['repeat_later'])
            assert len({continued['session_id'], repeated['session_id'], again['session_id'], later['session_id']}) == 4
            assert [event['id'] for event in saved['events'] if event['event_type'] == 'continuity' and event['state'] == 'active'] == [active[0]['id']]
            phase = 'source_deletion_and_unknown'
            for row in introduced:
                await manage('delete', id=row['id'])
            unknown, saved = await ask(sample['unknown'])
            assert not unknown['diagnostics']['selected_fact_ids'] and not saved['memories']
            assert re.search(r'不知道|不清楚|没有.{0,12}(?:信息|记录|记忆)|还看不出|不记得|无法.{0,8}(?:确定|判断)', unknown['tts_text'])
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
            'raw_response_review', 'shutdown_error_class', 'tool_results', 'B08_semantic_acceptance',
            'correction_original_id', 'correction_current_fact', 'correction_deleted_after_restart', 'correction_old_events',
            'retrieval_analysis', 'inflight_proof', 'recovery_proof'}
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
