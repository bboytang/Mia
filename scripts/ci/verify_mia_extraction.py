"""Installed SDK extraction -> real BGE -> atomic SQLite -> scoped context; fixture SSE/JSON."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx
import openai

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
from mia_companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from mia_companion.context import ContextBuilder, ContextError, ContextLimits
from mia_companion.embedding import SemanticEncoder
from mia_companion.extraction import LLMMemoryExtractor
from mia_companion.jobs import JobStore, MemoryWorker, TurnCompleted
from mia_companion.memory import MemoryError, MemoryStore
from mia_companion.semantic import SemanticMemoryIndex


class Policy:
    async def restore(self, snapshot):
        if snapshot != self.scope.snapshot():
            raise PrivateAuthorizationRequired()
        return self.scope

    async def require(self, scope, permission):
        if scope != self.scope or permission not in scope.permissions:
            raise PrivateAuthorizationRequired()


async def evaluate(args, report):
    import tempfile
    encoder = SemanticEncoder(args.model_dir)
    dataset = json.loads(args.dataset.read_text())
    report['dataset_sha256'] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    policy = Policy()
    scope = policy.scope = AuthenticatedScope('user:1:agent:extraction', 1, 1, 'extraction', 'mia', 'device', 'client', 0, 1,
        datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
    current, requests = None, []
    with tempfile.TemporaryDirectory() as folder:
        store = MemoryStore(Path(folder) / 'facts.sqlite3')
        index = SemanticMemoryIndex(store, encoder)
        def transport(request):
            body = json.loads(request.content)
            context = json.loads(body['messages'][1]['content'])
            assert 'FOREIGN_PRIVATE' not in request.content.decode()
            assert context['user_excerpts'] == [current['source']]
            requests.append({'case': current['id'], 'model': body['model']})
            assert body['stream'] is True
            chunk = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 0,
                'model': 'synthetic', 'choices': [{'index': 0, 'finish_reason': 'stop',
                    'delta': {'content': json.dumps(current['output'], ensure_ascii=False)}}]}
            return httpx.Response(200, headers={'content-type': 'text/event-stream'},
                content=('data: ' + json.dumps(chunk, ensure_ascii=False) + '\n\ndata: [DONE]\n\n').encode())
        def factory():
            provider = LLMProvider({'api_key': 'synthetic-only', 'model_name': 'synthetic',
                'base_url': 'https://ci.invalid/v4', 'max_tokens': 768, 'timeout': 5})
            provider.client.close()
            provider.client = openai.OpenAI(api_key='synthetic-only', base_url=provider.base_url, max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(transport)))
            return provider
        async def resolve(restored):
            assert restored == scope
            return LLMMemoryExtractor(factory)
        jobs = JobStore(store)
        worker = MemoryWorker(jobs, policy, resolve, encoder=encoder)
        # Foreign facts exist, but never enter extraction context or own RAG.
        store.apply_extraction('user:2:agent:other', 'other', 0, ['FOREIGN_PRIVATE'],
            {'memories': [{'category': 'fact', 'content': 'FOREIGN_PRIVATE', 'source_index': 0}]}, 'other')
        report['cases'] = []
        targets = {}
        for row in dataset['cases']:
            current = json.loads(json.dumps(row))
            if row['id'] == 'relation':
                current['output']['memories'][0]['relations'] = [{'target_id': targets['neutral'],
                    'relation': 'shared_term', 'anchor': '吃素', 'evidence': row['source']}]
            event = TurnCompleted(scope, 'ci-session', row['id'], row['id'], row['source'], store.snapshot(scope.owner)['revision'])
            start = len(requests)
            if row['expected'] == 'credential_rejected':
                try:
                    await worker.submit(event)
                except MemoryError as error:
                    assert error.code == 'credentials_forbidden'
                else:
                    raise AssertionError('Credential source persisted')
                report['cases'].append({'id': row['id'], 'state': 'credential_rejected', 'sdk_calls': 0})
                continue
            accepted = await worker.submit(event)
            assert accepted['status'] == 'accepted'
            if row['id'] == 'neutral':
                with patch.object(jobs, 'commit', side_effect=sqlite3.OperationalError('fixture rollback')):
                    await worker.run_once()
                assert jobs.current(accepted)['state'] == 'retry_wait'
                assert len(requests) - start == 1
                assert store.list_memories(scope.owner) == []
                with store.db:
                    store.db.execute('UPDATE mia_jobs SET next_attempt_at=0 WHERE id=?', (accepted['id'],))
            await worker.run_once()
            if row['expected'] == 'invalid':
                with store.db:
                    store.db.execute('UPDATE mia_jobs SET next_attempt_at=0 WHERE id=?', (accepted['id'],))
                await worker.run_once()
            task = jobs.current(accepted)
            expected = {'active': 'committed', 'pending': 'committed', 'empty': 'empty', 'invalid': 'failed'}[row['expected']]
            assert task['state'] == expected, (row['id'], task['state'], task['error_category'])
            details = {'id': row['id'], 'state': task['state'], 'sdk_calls': len(requests) - start}
            if expected == 'committed':
                source = store.db.execute('SELECT sm.memory_id,sm.source_type,m.confirmed,x.confirmation_origin '
                    'FROM mia_source_meta sm JOIN memories m ON m.id=sm.memory_id JOIN mia_memory_meta x ON x.memory_id=m.id '
                    'WHERE m.owner=? AND sm.turn_id=? AND sm.message_id=?', (scope.owner, row['id'], row['id'])).fetchone()
                assert source is not None
                targets[row['id']] = source['memory_id']
                assert bool(source['confirmed']) == (row['expected'] == 'active')
                indexed = store.db.execute('SELECT COUNT(*) FROM mia_vectors WHERE memory_id=?', (source['memory_id'],)).fetchone()[0]
                assert indexed == int(row['expected'] == 'active')
                if row['expected'] == 'active':
                    query = '周三在食堂怎么吃？' if row['id'] == 'neutral' else row['source']
                    found = await index.retrieve(scope, policy, query)
                    assert source['memory_id'] in [item['id'] for item in found['results']], (row['id'], 'RAG miss')
                    bundle = await ContextBuilder(index).build(scope, policy, 'context-' + row['id'], query,
                        limits=ContextLimits('synthetic', 16384, 768, 'CI synthetic capacity; not production'))
                    assert source['memory_id'] in bundle.diagnostics()['selected_fact_ids']
                    assert 'FOREIGN_PRIVATE' not in bundle.request_json
                else:
                    assert json.loads(task['validated_result']) == {'confirmation_required': True}
                details.update(source_type=source['source_type'], confirmation_origin=source['confirmation_origin'], indexed=bool(indexed))
            if row['expected'] == 'invalid':
                assert task['error_category'] == 'invalid_output' and task['attempts'] == 2
            assert task['source_payload'] == '{}'
            report['cases'].append(details)
        assert store.db.execute('SELECT COUNT(*) FROM mia_associations').fetchone()[0] == 1
        report['sdk_calls'] = len(requests)
        report['db_retry_did_not_repeat_model'] = report['cases'][0]['sdk_calls'] == 1
        report['confirmed_fact_count'] = store.db.execute('SELECT COUNT(*) FROM memories WHERE owner=? AND confirmed=1', (scope.owner,)).fetchone()[0]
        report['pending_fact_count'] = store.db.execute('SELECT COUNT(*) FROM memories WHERE owner=? AND confirmed=0', (scope.owner,)).fetchone()[0]
        # P18 uses the same installed SDK/Worker and actual BGE. Outputs remain fixtures.
        report['maintenance'] = []
        target = targets['neutral']
        second = MemoryStore(Path(folder) / 'facts.sqlite3')
        other_builder = ContextBuilder(SemanticMemoryIndex(second, encoder))
        limits = ContextLimits('synthetic', 16384, 768, 'CI synthetic capacity; not production')
        for mode, prefix, new in [('correction', '更正：', '我每周四都会在公司食堂吃素'),
                ('time_change', '以前：', '现在：我每周五都会在公司食堂吃素'),
                ('conflict', '不确定：', '我每周六都会在公司食堂吃素')]:
            old = store.db.execute('SELECT content FROM memories WHERE id=?', (target,)).fetchone()[0]
            cached = await other_builder.build(scope, policy, 'before-' + mode, old, limits=limits)
            text = prefix + old + '；' + new
            current = {'id': 'p18-' + mode, 'source': text, 'output': {'memories': [{
                'category': 'fact', 'content': new, 'source_quote': new, 'source_index': 0,
                'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False,
                'reconciliation': {'target_id': target, 'kind': mode, 'old_quote': old, 'evidence': text}}]}}
            event = TurnCompleted(scope, 'p18-session', current['id'], current['id'], text, store.snapshot(scope.owner)['revision'])
            accepted = await worker.submit(event)
            start = len(requests)
            if mode == 'correction':
                with patch.object(store, '_index', side_effect=sqlite3.OperationalError('p18 rollback')):
                    await worker.run_once()
                assert jobs.current(accepted)['state'] == 'retry_wait'
                assert store.db.execute('SELECT content FROM memories WHERE id=?', (target,)).fetchone()[0] == old
                with store.db:
                    store.db.execute('UPDATE mia_jobs SET next_attempt_at=0 WHERE id=?', (accepted['id'],))
            await worker.run_once()
            assert jobs.current(accepted)['state'] == 'committed', jobs.current(accepted)
            assert len(requests) - start == 1, 'DB retry called the model again'
            try:
                await other_builder.validate(cached, policy)
            except ContextError:
                pass
            else:
                raise AssertionError('Other connection retained old context')
            fresh = await other_builder.build(scope, policy, 'after-' + mode, new, limits=limits)
            assert old not in fresh.request_json
            if mode != 'conflict':
                assert new in fresh.request_json
                target = store.db.execute('SELECT id FROM memories WHERE owner=? AND content=?', (scope.owner, new)).fetchone()[0]
                assert store.db.execute('SELECT COUNT(*) FROM mia_vectors WHERE memory_id=?', (target,)).fetchone()[0] == 1
            else:
                assert new not in fresh.request_json
                assert json.loads(jobs.current(accepted)['validated_result']) == {'confirmation_required': True}
            report['maintenance'].append({'kind': mode, 'state': 'committed', 'sdk_calls': len(requests) - start,
                'old_context_rejected': True, 'old_fact_not_current': True})
        second.close()
        report['sdk_calls'] = len(requests)
        report['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        report['passed'] = True
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'code_sha': os.environ['GITHUB_SHA'], 'passed': False, 'kind': 'P17_installed_SDK_real_BGE_extraction',
        'chat_provider_calls': 0, 'model_outputs': 'synthetic_controlled_fixture', 'manager': 'policy_fixture_real_manager_separate',
        'resource_limit': {'cpu': 2, 'memory_mib': 2048, 'network': 'none'}, 'full_B03': 'not_accepted'}
    try:
        asyncio.run(evaluate(args, report))
    except Exception as error:
        import traceback
        report.update(error_class=type(error).__name__, failure=str(error), traceback=traceback.format_exc())
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}))
    if not report['passed']:
        raise SystemExit('P17 controlled extraction verification failed')


if __name__ == '__main__':
    main()
