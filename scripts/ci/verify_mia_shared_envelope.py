"""Real manager/MySQL/Redis/Python-BGE preflight, not full reply/Worker acceptance."""

import asyncio
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time
import traceback


sys.path.insert(0, str(Path(os.environ['MIA_SCOPE_UPSTREAM']) / 'main/xiaozhi-server'))
from config.manage_api_client import ManageApiClient
from mia_companion.authorization import PrivateAuthorization
from mia_companion.embedding import SemanticEncoder
from mia_companion.memory import MemoryStore
from mia_companion.retrieval import FEATURE_CACHE_BYTES
from mia_companion.semantic import SemanticMemoryIndex
from verify_mia_performance import populate, measure, summary


ROOT = Path(os.environ['MIA_P23_REPORT_DIR'])
CGROUP = Path('/sys/fs/cgroup/miap23.slice')


class TimedAuthorization(PrivateAuthorization):
    def __init__(self, config):
        super().__init__(config)
        self.timings = []

    async def _request(self, endpoint, body, timeout=3):
        started = time.perf_counter()
        try:
            return await super()._request(endpoint, body, timeout=timeout)
        finally:
            self.timings.append({'endpoint': endpoint,
                'elapsed_ms': (time.perf_counter() - started) * 1000})


def group_state():
    values = {name: (CGROUP / name).read_text().strip() for name in
        ('cpu.max', 'cpu.stat', 'memory.max', 'memory.swap.max', 'memory.current', 'memory.peak', 'memory.events')}
    return values


def members():
    pids = json.loads(os.environ['MIA_P23_DATABASE_PIDS'])
    pids.update(manager=int(os.environ['MIA_P23_MANAGER_PID']), python=os.getpid())
    result = {}
    for role, pid in pids.items():
        proc = Path('/proc') / str(pid)
        path = next(line[3:] for line in (proc / 'cgroup').read_text().splitlines() if line.startswith('0::'))
        assert path.startswith('/miap23.slice/'), 'A measured service escaped the common parent'
        status = (proc / 'status').read_text().splitlines()
        result[role] = {'pid': pid, 'cgroup': path, **{line.split(':')[0]: line.split(':', 1)[1].strip()
            for line in status if line.startswith(('VmRSS:', 'VmHWM:'))}}
    assert set(result) == {'mysql', 'redis', 'manager', 'python'}
    return result


def save(report):
    (ROOT / 'shared-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


async def compete(index, scopes, auth, queries):
    with index.store.lock, index.store.db:
        index.store.db.execute('DELETE FROM mia_vectors WHERE memory_id IN '
            '(SELECT id FROM memories WHERE owner=?)', (scopes[2].owner,))

    async def foreground(scope):
        samples = []
        for query in queries:
            for _ in range(5):
                started = time.perf_counter()
                value = await index.retrieve(scope, auth, query)
                samples.append((time.perf_counter() - started) * 1000)
                assert all(row['id'].startswith(scope.owner + '-') for row in value['candidates'])
        return {'scope_owner': scope.owner, **summary(samples)}

    started = time.perf_counter()
    results = await asyncio.gather(foreground(scopes[0]), foreground(scopes[1]),
        index.rebuild_batch(scopes[2], auth, limit=32), return_exceptions=True)
    results = [({'error_class': type(value).__name__, 'reason': str(value)}
        if isinstance(value, BaseException) else value) for value in results]
    return {'foreground': results[:2], 'rebuild': results[2],
        'elapsed_ms': (time.perf_counter() - started) * 1000,
        'scope': 'Two independent real-manager Scopes plus native reindex; no extraction Worker or Provider'}


async def evaluate(report):
    report.update(cgroup_before=group_state(), members_before=members())
    quota, period = report['cgroup_before']['cpu.max'].split()
    assert quota != 'max' and int(quota) / int(period) == 2, 'Shared CPU quota differs from frozen envelope'
    assert report['cgroup_before']['memory.max'] == '2147483648' and report['cgroup_before']['memory.swap.max'] == '0'
    config = {'manager-api': {'url': os.environ['MIA_SCOPE_MANAGER_URL'],
        'secret': os.environ['MIA_SCOPE_SERVER_SECRET']}}
    ManageApiClient(config)
    auth = TimedAuthorization(config)
    peers = json.loads(os.environ['MIA_P23_PEERS'])
    scopes = [await auth.verify(peer['device_id'], peer['client_id'], peer['private_credential']) for peer in peers]
    report['authorization_bootstrap_requests'] = auth.timings
    assert len({scope.owner for scope in scopes}) == 3
    report['authorized_owners'] = [scope.owner for scope in scopes]
    started = time.perf_counter()
    encoder = SemanticEncoder(Path(os.environ['MIA_EMBEDDING_DIR']))
    report['encoder_cold_load_ms'] = (time.perf_counter() - started) * 1000
    dataset = Path(__file__).resolve().parents[2] / 'server/tests/fixtures/persona_memory_performance_p23_v1.json'
    fixture = json.loads(dataset.read_text())
    report['dataset_sha256'] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    report['embedding'] = {'model_id': encoder.model_id, 'revision': encoder.revision, 'dimension': encoder.dimension}
    vectors = {(i, profile): encoder.encode(seed[profile]).astype('<f4')
        for i, seed in enumerate(fixture['records']) for profile in ('short', 'dense')}
    report['capacity'] = []
    save(report)
    for size in ((10000,) if report['mode'] == 'diagnostic' else (1000, 10000)):
        started, cpu_started = time.monotonic(), time.process_time()
        row = {'size_per_frontend_scope': size, 'profile': 'dense', 'cgroup_before': group_state()}
        auth.timings = []
        row['authorization_requests'] = auth.timings
        report['capacity'].append(row)
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'memory.sqlite3')
            try:
                for scope, count in zip(scopes, (size, size, 32)):
                    populate(store, scope, count, 'dense', fixture, vectors)
                index = SemanticMemoryIndex(store, encoder)
                if report['mode'] == 'diagnostic':
                    from mia_performance_diagnostics import diagnose
                    # diagnose warms the first owner itself. Warm the other owner
                    # too, retaining both real Scopes in the same bounded cache.
                    for query in fixture['queries']:
                        await index.retrieve(scopes[1], auth, query)
                    row['diagnostics'] = await diagnose(index, scopes[0], auth, fixture['queries'], summary,
                        lambda: compete(index, scopes, auth, fixture['queries']))
                    row['authorization_requests_scope'] = 'Whole diagnostic including separate profile; not timed acceptance'
                else:
                    row['sequential'] = []
                    for scope in scopes[:2]:
                        row['sequential'].append(await measure(index, scope, auth, fixture['queries']))
                        save(report)
                    # Each Scope/query was warmed above; competition uses distinct owners.
                    row['competition'] = await compete(index, scopes, auth, fixture['queries'])
                row['rss_peak_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                row['static_features'] = {'entries': len(index._features.entries), 'accounted_bytes': index._features.bytes,
                    'entries_by_owner': dict(Counter(key[0] for key in index._features.entries))}
                row['integrity'] = store.db.execute('PRAGMA integrity_check').fetchone()[0]
                if report['mode'] == 'capacity':
                    row['within_numeric_budgets'] = (all(case['encode_hybrid']['p95_ms'] <= 400
                        and (size != 10000 or case['sqlite_exact']['p95_ms'] <= 150)
                        for owner in row['sequential'] for case in owner['queries'])
                        and all('error_class' not in value and value['p95_ms'] <= 400
                            for value in row['competition']['foreground'])
                        and row['rss_peak_mib'] <= 512 and row['integrity'] == 'ok'
                        and row['competition']['rebuild'].get('indexed') == 32)
                row['wall_seconds'] = time.monotonic() - started
                row['python_cpu_seconds'] = time.process_time() - cpu_started
                row['cgroup_after'] = group_state()
                row['members_after'] = members()
                save(report)
            finally:
                store.close()
    events = dict(line.split() for line in group_state()['memory.events'].splitlines())
    assert int(events['oom']) == int(events['oom_kill']) == 0, 'Shared envelope had OOM events'
    if report['mode'] == 'capacity':
        report['shared_envelope_preflight_passed'] = all(row['within_numeric_budgets'] for row in report['capacity'])
    else:
        report['diagnostic_complete'] = True


def main():
    mode = os.environ.get('MIA_P23_MODE', 'capacity')
    assert mode in ('capacity', 'diagnostic')
    report = {'code_sha': os.environ['GITHUB_SHA'], 'mode': mode,
        'shared_envelope_preflight_passed': False, 'diagnostic_complete': False,
        'p23_complete': False, 'provider_requests': 0,
        'runtime_profile': {'java_max_heap_mib': 512, 'java_max_metaspace_mib': 256,
            'java_active_processor_count': 2, 'java_thread_stack_kib': 512,
            'java_logging': 'ERROR on all existing loggers before synthetic authorization setup',
            'static_cache_budget_bytes': FEATURE_CACHE_BYTES,
            'mysql': 'mysql:8.4 default server with loopback bind', 'redis': 'redis:8 loopback bind',
            'upstream_sha': '87c6df77b0220ddbd8fc804f984f83f69f3225e5'},
        'scope': 'Actual manager/TLS/authorization, MySQL, Redis and Python/BGE share one 2CPU/2GiB parent; bridge/audio/app lifecycle not exercised',
        'fixture_kind': 'Synthetic metadata and numbered facts with replicated actual BGE seed vectors; capacity only, no semantic-quality claim',
        'remaining': ['same-Provider paired first-sentence delta', 'actual reply/app path under shared resources',
            'real persistent Worker task fairness/faults/120-second terminal latency', 'inflight total service shutdown within 20 seconds']}
    save(report)
    try:
        asyncio.run(evaluate(report))
    except Exception as error:
        report.update(error_class=type(error).__name__, reason=str(error), traceback=traceback.format_exc())
    finally:
        report['cgroup_final'] = group_state()
        save(report)
    print(json.dumps({name: report[name] for name in ('mode', 'shared_envelope_preflight_passed', 'diagnostic_complete', 'p23_complete', 'provider_requests')}))
    if not report['diagnostic_complete' if mode == 'diagnostic' else 'shared_envelope_preflight_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
