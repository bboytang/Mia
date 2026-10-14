"""Real-vector P06 experiment, deliberately separate from production RAG.

Only calibration queries select rejection thresholds. A successful job means the
experiment ran; the report's eligible field, not the job status, gates selection.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import resource
import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class Embedder:
    def __init__(self, directory, variant):
        self.metadata = json.loads((directory / 'metadata.json').read_text())
        path = directory / variant
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        assert digest.hexdigest() == self.metadata['models'][variant]['sha256']
        self.tokenizer = Tokenizer.from_file(str(directory / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
        self.inputs = {item.name for item in self.session.get_inputs()}

    def encode(self, text, query=False):
        if query:
            text = self.metadata['query_prefix'] + text
        tokens = self.tokenizer.encode(text)
        values = {'input_ids': np.array([tokens.ids], dtype=np.int64),
                  'attention_mask': np.array([tokens.attention_mask], dtype=np.int64),
                  'token_type_ids': np.array([tokens.type_ids], dtype=np.int64)}
        output = self.session.run(None, {name: values[name] for name in self.inputs})[0]
        vector = output[0, 0].astype(np.float32)
        length = float(np.linalg.norm(vector))
        assert np.isfinite(vector).all() and length > 0
        assert vector.shape == (self.metadata['dimension'],)
        return vector / length


def bigrams(text):
    compact = re.sub(r'\s+', '', text.lower())
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def expand(query, memories):
    terms = []
    for item in memories:
        if any(len(term) >= 2 and term in query for term in item['triggers']):
            terms.extend([item['entity'], *item['keywords']])
    terms = list(dict.fromkeys(terms))[:8]
    return query + ('。关联线索：' + '、'.join(terms) if terms else ''), terms


def signals(query, expanded, item, cosine):
    terms = list(dict.fromkeys([item['entity'], *item['keywords'], *item['triggers']]))
    hits = sum(len(term) >= 2 and term in expanded for term in terms)
    left = bigrams(expanded)
    right = bigrams(item['content'] + item['entity'] + ''.join(item['keywords']))
    overlap = len(left & right) / max(1, len(left | right))
    return [max(0.0, min(1.0, float(cosine))),
            min(1.0, overlap * 2.2 + min(0.7, hits * 0.14)),
            min(1.0, sum(len(t) >= 2 and t in query for t in item['triggers']) * 0.35),
            item['weight'] / 10.0]


def rank(case, threshold, floor, disabled=None):
    weights = [0.58, 0.28, 0.08, 0.06]
    rows = []
    for item in case['candidates']:
        score = sum(w * s for i, (w, s) in enumerate(zip(weights, item['signals'])) if i != disabled)
        if score >= threshold and item['signals'][0] >= floor:
            rows.append((score, item['id']))
    return [item[1] for item in sorted(rows, reverse=True)[:4]]


def metrics(cases, threshold, floor):
    positives = [c for c in cases if c['expected']]
    negatives = [c for c in cases if not c['expected']]
    predictions = {c['id']: rank(c, threshold, floor) for c in cases}
    return {
        'positive_count': len(positives), 'negative_count': len(negatives),
        'complete_recall_at_4': sum(set(c['expected']) <= set(predictions[c['id']])
                                    for c in positives) / max(1, len(positives)),
        'top1': sum(bool(predictions[c['id']]) and predictions[c['id']][0] in c['expected']
                    for c in positives) / max(1, len(positives)),
        'empty_recall': sum(not predictions[c['id']] for c in negatives) / max(1, len(negatives)),
    }


def timings(values):
    return {'count': len(values), 'p50_ms': float(np.percentile(values, 50)),
            'p95_ms': float(np.percentile(values, 95))}


def load_vectors(connection, scope, dimension):
    rows = connection.execute('SELECT id, vector FROM vectors WHERE scope=?', (scope,)).fetchall()
    if not rows:
        return [], np.empty((0, dimension), dtype=np.float32)
    return [row[0] for row in rows], np.vstack([np.frombuffer(row[1], dtype=np.float32) for row in rows])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text())
    memories = dataset['memories']
    queries = dataset['queries']
    ids = {item['id']: item for item in memories}
    assert len(ids) == len(memories)
    assert len({q['id'] for q in queries}) == len(queries)
    for query in queries:
        assert query['split'] in {'calibration', 'holdout'}
        for key in query['expected']:
            assert ids[key]['scope'] == query['scope'] and ids[key]['state'] == 'active'
    started = time.perf_counter()
    embedder = Embedder(args.model_dir, args.variant)
    cold_ms = (time.perf_counter() - started) * 1000
    embedder.encode('预热查询', query=True)
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE vectors (id TEXT PRIMARY KEY, scope TEXT NOT NULL, vector BLOB NOT NULL)')
    connection.execute('CREATE INDEX vector_scope ON vectors(scope)')
    for item in memories:
        if item['state'] == 'active':
            vector = embedder.encode(item['content'])
            connection.execute('INSERT INTO vectors VALUES (?,?,?)',
                               (item['id'], item['scope'], vector.tobytes()))
    connection.commit()
    cases, latency, no_expansion_hits = [], [], []
    for query in queries:
        eligible = [m for m in memories if m['state'] == 'active' and m['scope'] == query['scope']]
        expanded, terms = expand(query['query'], eligible)
        names, matrix = load_vectors(connection, query['scope'], embedder.metadata['dimension'])
        plain = matrix @ embedder.encode(query['query'], query=True)
        plain_ids = [names[i] for i in np.argsort(plain)[::-1][:4]]
        if query['expected'] and query['split'] == 'holdout':
            no_expansion_hits.append(set(query['expected']) <= set(plain_ids))
        for _ in range(5):
            start = time.perf_counter()
            expanded, terms = expand(query['query'], eligible)
            vector = embedder.encode(expanded, query=True)
            names, matrix = load_vectors(connection, query['scope'], embedder.metadata['dimension'])
            cosine = matrix @ vector
            selected = np.argsort(cosine)[::-1][:12]
            candidates = [{'id': names[i], 'signals': signals(query['query'], expanded, ids[names[i]], cosine[i])}
                          for i in selected]
            latency.append((time.perf_counter() - start) * 1000)
        cases.append({**query, 'expansion': terms, 'candidates': candidates})
    calibration = [c for c in cases if c['split'] == 'calibration']
    holdout = [c for c in cases if c['split'] == 'holdout']
    best = None
    for threshold in np.arange(0.30, 0.91, 0.01):
        for floor in np.arange(0.30, 0.86, 0.025):
            measured = metrics(calibration, float(threshold), float(floor))
            key = (min(measured['complete_recall_at_4'], measured['empty_recall']),
                   measured['complete_recall_at_4'] + measured['empty_recall'], measured['top1'], threshold, floor)
            if best is None or key > best[0]:
                best = (key, float(threshold), float(floor), measured)
    _, threshold, floor, calibration_metrics = best
    measured = metrics(holdout, threshold, floor)
    for case in cases:
        case['retrieved'] = rank(case, threshold, floor)
        assert all(ids[key]['scope'] == case['scope'] and ids[key]['state'] == 'active'
                   for key in case['retrieved'])
    ablation = {name: sum(rank(c, threshold, floor, i) != c['retrieved'] for c in holdout)
                for i, name in enumerate(['semantic', 'lexical', 'association', 'emotion'])}
    stress = {}
    reference = next(m for m in memories if m['state'] == 'active')
    seed = embedder.encode(reference['content'])
    with tempfile.TemporaryDirectory() as temporary:
        db = sqlite3.connect(str(Path(temporary) / 'stress.sqlite3'))
        db.execute('CREATE TABLE vectors (id INTEGER PRIMARY KEY, scope TEXT, vector BLOB)')
        db.execute('CREATE INDEX vector_scope ON vectors(scope)')
        for count in [1000, 10000, 50000]:
            db.execute('DELETE FROM vectors')
            db.executemany('INSERT INTO vectors VALUES (?,?,?)',
                           ((i, 'A/travel/mia' if i < count else 'B/travel/mia', seed.tobytes())
                            for i in range(2 * count)))
            db.commit()
            samples = []
            for _ in range(5):
                start = time.perf_counter()
                names, matrix = load_vectors(db, 'A/travel/mia', seed.shape[0])
                assert len(names) == count
                np.argsort(matrix @ seed)[-12:]
                samples.append((time.perf_counter() - start) * 1000)
            stress[str(count)] = timings(samples)
            stress[str(count)]['database_bytes'] = (Path(temporary) / 'stress.sqlite3').stat().st_size
        db.close()
    rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    report = {'code_sha': os.environ.get('GITHUB_SHA'), 'dataset_version': dataset['version'],
              'dataset_sha256': hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
              'model': embedder.metadata, 'variant': args.variant, 'python': platform.python_version(),
              'runtime_packages': {n: importlib.metadata.version(n) for n in ['numpy', 'onnxruntime', 'tokenizers']},
              'limits': {'cpu': 2, 'memory_gib': 2}, 'cold_load_ms': cold_ms,
              'peak_rss_mib': rss_mib, 'query_pipeline': timings(latency), 'sqlite_stress': stress,
              'threshold': threshold, 'semantic_floor': floor, 'calibration': calibration_metrics,
              'holdout': measured, 'pure_vector_positive_recall_at_4': sum(no_expansion_hits) / len(no_expansion_hits),
              'ablation_changed_holdout_predictions': ablation, 'cases': cases,
              'scope_or_lifecycle_violations': 0,
              'note': 'Prototype experiment only; not production RAG or eight-capability acceptance.'}
    report['eligible'] = (measured['complete_recall_at_4'] >= 0.90 and measured['top1'] >= 0.80
                          and measured['empty_recall'] >= 0.95 and rss_mib <= 512
                          and report['query_pipeline']['p95_ms'] <= 400
                          and stress['10000']['p95_ms'] <= 150)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: report[k] for k in ['variant', 'eligible', 'holdout', 'query_pipeline', 'peak_rss_mib']},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
