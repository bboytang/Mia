"""Four bounded P17 provider samples; synthetic data and vector fixtures, no production."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
from urllib.parse import urlsplit

import httpx
import numpy as np

sys.path.insert(0, str(Path(os.environ['MIA_EXTRACTION_UPSTREAM']) / 'main/xiaozhi-server'))
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
from mia_companion.authorization import AuthenticatedScope
from mia_companion.embedding import DIMENSION, MODEL_KEY, REVISION
from mia_companion.extraction import LLMMemoryExtractor
from mia_companion.jobs import JobStore, MemoryWorker, TurnCompleted
from mia_companion.memory import MemoryStore


class UnitEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION

    def encode(self, text, query=False):
        vector = np.zeros(DIMENSION, dtype=np.float32)
        vector[0] = 1
        return vector


class Policy:
    async def restore(self, snapshot):
        assert snapshot == self.scope.snapshot()
        return self.scope

    async def require(self, scope, permission):
        assert scope == self.scope and permission in scope.permissions


def deadline(*unused):
    raise TimeoutError('Bounded P17 provider verification expired')


async def evaluate(report, secret):
    base, model = os.environ['MIA_TEST_LLM_BASE_URL'], os.environ['MIA_TEST_LLM_MODEL']
    url = urlsplit(base)
    if (not secret or url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment):
        raise ValueError('Dedicated HTTPS test configuration is missing or invalid')
    report.update(provider_host=url.hostname, configured_model=model)
    outputs = []
    def factory():
        if report['requests'] >= 4:
            raise ValueError('P17 request budget exhausted')
        report['requests'] += 1
        provider = LLMProvider({'api_key': secret, 'base_url': base, 'model_name': model, 'max_tokens': 768,
                                'temperature': 0.1, 'timeout': 30})
        original = provider.client
        provider.client = original.with_options(max_retries=0,
            http_client=httpx.Client(timeout=30, follow_redirects=False))
        original.close()
        original_response = provider.response_no_stream
        def capture(system, user):
            output = original_response(system, user)
            outputs.append(output.replace(secret, '[REDACTED]') if isinstance(output, str) else 'non_text_output')
            return output
        provider.response_no_stream = capture
        return provider
    policy = Policy()
    policy.scope = AuthenticatedScope('user:1:agent:p17-live-fixture', 1, 1, 'p17-live-fixture', 'mia', 'device', 'client', 0, 1,
        datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
    cases = [('neutral_durable', '我每周三都会在公司食堂吃素', 'active'),
             ('medical_confirmation', '我被确诊为糖尿病', 'pending'),
             ('quoted_fiction', '这只是小说台词：“我住在月球”；不要把它记成我的真实经历', 'empty'),
             ('ongoing_goal', '我计划接下来半年每周练习游泳', 'active')]
    with tempfile.TemporaryDirectory() as folder:
        store = MemoryStore(Path(folder) / 'facts.sqlite3')
        async def resolve(scope):
            return LLMMemoryExtractor(factory)
        jobs = JobStore(store)
        worker = MemoryWorker(jobs, policy, resolve, encoder=UnitEncoder())
        for name, text, expected in cases:
            admitted = await worker.submit(TurnCompleted(policy.scope, 'live-synthetic', name, name, text, 0))
            started = time.perf_counter()
            await worker.run_once()  # No evaluation retry or parameter tuning.
            task = jobs.current(admitted)
            found = store.db.execute('SELECT m.content,m.confirmed FROM memories m JOIN mia_source_meta s ON s.memory_id=m.id '
                'WHERE m.owner=? AND s.message_id=?', (policy.scope.owner, name)).fetchall()
            passed = (task['state'] == 'empty' and not found if expected == 'empty' else
                task['state'] == 'committed' and bool(found) and all(bool(row['confirmed']) == (expected == 'active') for row in found))
            if expected == 'pending' and passed:
                passed = json.loads(task['validated_result']) == {'confirmation_required': True}
            report['cases'].append({'name': name, 'source': text, 'expected': expected, 'state': task['state'],
                'error_category': task['error_category'], 'pipeline_semantic_pass': passed, 'model_output': outputs[-1] if outputs else '',
                'stored': [dict(row) for row in found], 'elapsed_ms': (time.perf_counter() - started) * 1000})
            if not passed:
                raise AssertionError('P17 provider sample did not pass; no retry performed')
        report['passed'] = True
        store.close()


def main():
    report = {'code_sha': os.environ.get('GITHUB_SHA'), 'upstream_sha': '87c6df77b0220ddbd8fc804f984f83f69f3225e5',
        'kind': 'P17_real_installed_provider_structured_extraction', 'passed': False, 'requests': 0, 'cases': [],
        'limits': {'maximum_requests': 4, 'max_output_tokens': 768, 'http_timeout_seconds': 30,
                   'total_deadline_seconds': 150, 'retries': 0},
        'fixtures': 'Synthetic user excerpts, policy and unit vectors; actual BGE and manager tested separately',
        'full_B03': 'not_accepted', 'full_B08': 'not_accepted', 'production_deployment': 'not_performed'}
    secret = os.environ.get('MIA_TEST_LLM_API_KEY', '')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(150)
    try:
        asyncio.run(evaluate(report, secret))
    except Exception as error:
        report['error_class'] = type(error).__name__
    finally:
        signal.alarm(0)
        Path(os.environ['MIA_EXTRACTION_REPORT']).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'requests': report['requests'], 'cases': len(report['cases'])}))
    if not report['passed']:
        raise SystemExit('P17 bounded provider samples failed; inspect sanitized artifact')


if __name__ == '__main__':
    main()
