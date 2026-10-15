"""Bounded real dialogue and real-date observation evidence, using only CI test data."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import httpx
import numpy as np

sys.path.insert(0, str(Path(os.environ['MIA_CONTINUITY_UPSTREAM']) / 'main/xiaozhi-server'))
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

from core.providers.llm.openai.openai import LLMProvider
from mia_companion import emotions, reply
from mia_companion.authorization import AuthenticatedScope
from mia_companion.context import ContextBuilder
from mia_companion.embedding import DIMENSION, MODEL_KEY, REVISION
from mia_companion.extraction import LLMMemoryExtractor
from mia_companion.jobs import JobStore, MemoryWorker, TurnCompleted
from mia_companion.memory import MemoryStore
from mia_companion.persona import PersonaGuardrail
from mia_companion.semantic import SemanticMemoryIndex


class UnitEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION
    def encode(self, text, query=False):
        result = np.zeros(DIMENSION, dtype=np.float32)
        result[0] = 1
        return result


class Policy:
    def __init__(self):
        self.scope = AuthenticatedScope('user:1:agent:continuity-ci', 1, 1, 'continuity-ci', 'mia', 'test-device', 'test-client',
            0, 1, datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
    async def require(self, scope, permission):
        assert scope == self.scope and permission in scope.permissions
    async def restore(self, snapshot):
        assert snapshot == self.scope.snapshot()
        return self.scope


def provider(report, output=768):
    from urllib.parse import urlsplit
    secret, base, model = (os.environ['MIA_TEST_LLM_' + key] for key in ('API_KEY', 'BASE_URL', 'MODEL'))
    url = urlsplit(base)
    assert secret and url.scheme == 'https' and url.hostname and not (url.username or url.password or url.query or url.fragment)
    assert report['requests'] < 10
    report['requests'] += 1
    result = LLMProvider({'api_key': secret, 'base_url': base, 'model_name': model, 'max_tokens': output,
                          'temperature': 0.1, 'timeout': 30})
    original = result.client
    result.client = original.with_options(max_retries=0, http_client=httpx.Client(timeout=30, follow_redirects=False))
    original.close()
    return result


async def extract(store, policy, text, marker, report):
    outputs = []
    def factory():
        result = provider(report)
        original = result.response_no_stream
        def capture(system, user):
            output = original(system, user)
            outputs.append(output)
            return output
        result.response_no_stream = capture
        return result
    async def resolve(scope):
        return LLMMemoryExtractor(factory)
    jobs = JobStore(store)
    worker = MemoryWorker(jobs, policy, resolve, encoder=UnitEncoder())
    task = await worker.submit(TurnCompleted(policy.scope, 'session-' + marker, marker, marker, text,
        store.snapshot(policy.scope.owner)['revision']))
    await worker.run_once()
    row = jobs.current(task)
    report['cases'].append({'phase': marker, 'source': text, 'model_output': outputs[-1] if outputs else None,
        'state': row['state'], 'error_category': row['error_category'], 'server_observed_at': row['created_at']})
    assert row['state'] in {'committed', 'empty'}, row['error_category']


async def converse(store, policy, marker, query, report):
    llm = provider(report, 256)
    profile = Path(os.environ['MIA_CONTINUITY_DIR']) / 'profile.json'
    profile.write_text(json.dumps({'provider_module': type(llm).__module__, 'base_url': llm.base_url,
        'model': llm.model_name, 'context_window': 8192,
        'capacity_source': 'Isolated bounded evaluation envelope, short accepted real requests; not production model capacity evidence'}))
    os.environ['MIA_CONTEXT_PROFILE_FILE'] = str(profile)
    message = SimpleNamespace(role='user', content=query, uniq_id=marker, is_temporary=False, tool_calls=None, tool_call_id=None)
    conn = SimpleNamespace(read_config_from_api=True, _mia_scope=policy.scope, _mia_authorization=policy,
        _mia_context_builder=ContextBuilder(SemanticMemoryIndex(store, UnitEncoder())), llm=llm,
        sentence_id=marker, session_id='session-' + marker, dialogue=SimpleNamespace(dialogue=[message]),
        loop=asyncio.get_running_loop(), client_abort=False)
    try:
        chunks = await asyncio.to_thread(lambda: list(reply.response(conn, None, 0)))
        text = ''.join(chunks)
        assert text.strip() and not PersonaGuardrail().inspect_output(text)[1]
        turn = conn._mia_context_turn
        event_ids = await turn.builder.complete(turn.bundle, policy, text)
        report['cases'].append({'phase': marker, 'source': query, 'model_output': text,
            'events_before': turn.bundle.diagnostics()['events'], 'events_activated': event_ids,
            'trend_status': turn.bundle.diagnostics()['trends'], 'selected_fact_ids': turn.bundle.diagnostics()['selected_fact_ids'],
            'estimated_input': turn.bundle.diagnostics()['estimated_input']})
        return text, turn.bundle
    finally:
        llm.client.close()


async def stage(name, report):
    root = Path(os.environ['MIA_CONTINUITY_DIR'])
    store = MemoryStore(root / 'state.sqlite3')
    policy = Policy()
    owner = policy.scope.owner
    try:
        if name == 'seed':
            await extract(store, policy, '我喜欢蓝色', name, report)
            assert any(row['confirmed'] and '蓝色' in row['content'] for row in store.list_memories(owner))
        elif name in {'continuity', 'repeat', 'reflection', 'boundary', 'deleted', 'insufficient'}:
            query = {'continuity': '你还记得我喜欢蓝色吗', 'repeat': '你还记得我喜欢蓝色吗，不用重新介绍',
                'reflection': '你怎么看我喜欢蓝色这件事', 'boundary': '请不要叫我宝贝',
                'deleted': '你还记得我以前喜欢哪种颜色吗', 'insufficient': '你能从长期记录判断我最近的心情趋势吗'}[name]
            if name == 'deleted':
                for row in store.list_memories(owner):
                    store.delete_memory(owner, row['id'])
            text, bundle = await converse(store, policy, name, query, report)
            case = report['cases'][-1]
            if name in {'continuity', 'reflection', 'boundary'}:
                assert case['events_activated'], 'Actual completed response did not confirm candidate'
            elif name == 'repeat':
                assert not case['events_activated'] and any(item['state'] == 'active' for item in case['events_before'])
                assert store.db.execute("SELECT COUNT(*) FROM mia_events WHERE event_type='continuity'").fetchone()[0] == 1
            elif name == 'deleted':
                assert not case['selected_fact_ids'] and not any(item['state'] == 'active' and item['type'] != 'boundary'
                    for item in json.loads(bundle.inputs_json)['events'])
            elif name == 'insufficient':
                assert case['trend_status'] == 'insufficient_observations'
        elif name in {'default-off', 'enabled-mood', 'quoted-mood', 'daily'}:
            if name == 'enabled-mood':
                store.handle(owner, {'action': 'emotion_consent', 'enabled': True})
            if name == 'daily':
                if not emotions.consent(store, owner)['enabled']:
                    store.handle(owner, {'action': 'emotion_consent', 'enabled': True})
                day = int(store.clock()) // 86400
                rows = store.db.execute('SELECT DISTINCT observed_at/86400 FROM mia_observations WHERE owner=?', (owner,)).fetchall()
                assert all(row[0] != day for row in rows), 'One real-date observation run per UTC day'
                assert len(rows) < 7, 'Seven-day collection budget already reached'
                name = 'daily-' + str(day)
            text = '这只是小说台词：“我今天很难过”，不是我的真实心情' if name == 'quoted-mood' else '我今天很难过'
            before = store.db.execute('SELECT COUNT(*) FROM mia_observations WHERE owner=?', (owner,)).fetchone()[0]
            await extract(store, policy, text, name, report)
            after = store.db.execute('SELECT COUNT(*) FROM mia_observations WHERE owner=?', (owner,)).fetchone()[0]
            assert after == before + int(name == 'enabled-mood' or name.startswith('daily-'))
            report['emotion_status'] = store.handle(owner, {'action': 'emotion_status'})
        else:
            raise ValueError('Unknown verification phase')
    finally:
        store.close()


def main():
    root = Path(os.environ['MIA_CONTINUITY_DIR'])
    root.mkdir(parents=True, exist_ok=True)
    target = root / 'provider-results.json'
    report = json.loads(target.read_text()) if target.exists() else {'code_sha': os.environ['GITHUB_SHA'],
        'requests': 0, 'cases': [], 'passed': False, 'actual_clock': True,
        'fixtures': 'Synthetic test user, policy and unit vectors; installed reply bridge and real provider. Actual BGE/manager separate.',
        'production_context_limits': 'unverified; isolated 8192-byte conservative test envelope only',
        'full_B05_B07_B08': 'not_accepted'}
    name = os.environ.get('MIA_CONTINUITY_STAGE')
    if name:
        try:
            asyncio.run(stage(name, report))
            report['passed'] = True
        except Exception as error:
            report.update(passed=False, error_class=type(error).__name__, failed_phase=name)
        finally:
            secret = os.environ['MIA_TEST_LLM_API_KEY']
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2).replace(secret, '[REDACTED]') + '\n')
        if not report['passed']:
            raise SystemExit('Bounded continuity phase failed; inspect sanitized artifact')
        return
    phases = ['daily'] if os.environ.get('MIA_CONTINUITY_MODE') == 'daily' else [
        'seed', 'continuity', 'repeat', 'reflection', 'boundary', 'deleted', 'default-off', 'enabled-mood', 'insufficient', 'quoted-mood']
    for phase in phases:
        env = dict(os.environ, MIA_CONTINUITY_STAGE=phase)
        # Each phase starts a NEW Python process, restoring only the persisted DB.
        result = subprocess.run([sys.executable, __file__], env=env, timeout=45, capture_output=True)
        if result.returncode:
            raise SystemExit('Bounded continuity verification stopped; inspect sanitized artifact')
    if phases == ['daily']:
        report = json.loads(target.read_text())
        import hashlib
        report.update(collection_run_id=os.environ['GITHUB_RUN_ID'], completed_at=datetime.now(timezone.utc).isoformat(),
            mode='daily', code_sha=os.environ['GITHUB_SHA'], previous_run=os.environ.get('MIA_CONTINUITY_PREVIOUS_RUN') or None,
            state_sha256=hashlib.sha256((root / 'state.sqlite3').read_bytes()).hexdigest(),
            real_longitudinal_complete=report['emotion_status']['trend']['status'] == 'available')
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'phases': len(phases), 'passed': True, 'clock': 'real', 'process_restart_between_phases': True}))


if __name__ == '__main__':
    main()
