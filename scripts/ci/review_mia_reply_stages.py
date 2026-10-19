"""Offline attribution of frozen replies; preserve source timings and verdicts."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics

from mia_tts_timing import stage_durations


def review(source):
    compressed = source.read_bytes()
    raw = gzip.decompress(compressed)
    child = json.loads(raw)
    pairs = {}
    for sample in child['cases']:
        key, variant = sample['case'].rsplit('-', 1)
        pairs.setdefault(key, {})[variant] = sample
    result = {'source_sha': child['code_sha'], 'source_file': source.name,
        'source_sha256': hashlib.sha256(compressed).hexdigest(),
        'source_raw_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Corrected offline attribution only; no new requests or changed total latency/verdict.',
        'timing_origins': 'v2 first-content is SDK-relative; SDK-start/TTS-ready are case-relative.',
        'limitations': 'SDK interval includes remote, transport, consumer and observer cost; component percentiles do not add.',
        'pairs': [], 'groups': []}
    for key, samples in pairs.items():
        assert set(samples) == {'baseline', 'memory'}
        baseline, memory = samples['baseline'], samples['memory']
        assert all(baseline[k] == memory[k] for k in ('capacity', 'query', 'warm'))
        row = {'case': key, **{k: baseline[k] for k in ('capacity', 'query', 'warm')}}
        for variant, sample in samples.items():
            row[variant] = stage_durations(sample)
        row['delta'] = {k: row['memory'][k] - row['baseline'][k] for k in row['baseline']}
        row['first_sentence_delta_ms'] = memory['first_sentence_ms'] - baseline['first_sentence_ms']
        assert abs(sum(row['delta'].values()) - row['first_sentence_delta_ms']) < 1e-6
        result['pairs'].append(row)
    for capacity, query in dict.fromkeys((r['capacity'], r['query']) for r in result['pairs']):
        rows = [r for r in result['pairs'] if r['capacity'] == capacity and r['query'] == query and not r['warm']]
        assert len(rows) == 5
        result['groups'].append({'capacity': capacity, 'query': query, 'count': len(rows),
            'total_delta_p95_ms': statistics.quantiles([r['first_sentence_delta_ms'] for r in rows], n=100, method='inclusive')[94],
            'component_delta_p50_ms': {k: statistics.median(r['delta'][k] for r in rows) for k in rows[0]['delta']},
            'worst_pair': max(rows, key=lambda r: r['first_sentence_delta_ms'])})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error('Output must be a new file; original evidence is immutable')
    args.output.write_text(json.dumps(review(args.source), ensure_ascii=False, indent=2) + '\n')
