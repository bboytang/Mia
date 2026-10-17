"""Reassess unchanged archived measurements under the user-approved D08 v2."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

from mia_performance_budgets import LIMITS, REVISION, within_budgets


def validate_samples(value):
    if isinstance(value, dict):
        if 'samples_ms' in value:
            assert value['count'] == len(value['samples_ms'])
        for child in value.values():
            validate_samples(child)
    elif isinstance(value, list):
        for child in value:
            validate_samples(child)


def review(path, shared):
    archive = path.read_bytes()
    raw = gzip.decompress(archive)
    report = json.loads(raw)
    assert report['mode'] == 'capacity' and 'error_class' not in report
    assert len(report['capacity']) == (2 if shared else 5)
    group = report['cgroup_final' if shared else 'cgroup_after']
    assert group['cpu.max'] == '200000 100000' and group['memory.max'] == '2147483648'
    events = dict(line.split() for line in group['memory.events'].splitlines())
    assert events['oom'] == events['oom_kill'] == '0'
    validate_samples(report)
    rows = [{'size': row['size_per_frontend_scope' if shared else 'size_per_scope'],
        'profile': row['profile'], 'required': row.get('required', True),
        'original_within_numeric_budgets': row['within_numeric_budgets'],
        'within_numeric_budgets_v2': within_budgets(row, shared=shared)} for row in report['capacity']]
    return {'runtime_sha': report['code_sha'], 'source': str(path),
        'raw_sha256': hashlib.sha256(raw).hexdigest(), 'archive_sha256': hashlib.sha256(archive).hexdigest(),
        'original_gate_passed': report['shared_envelope_preflight_passed' if shared else 'numeric_gate_passed'],
        'numeric_gate_passed_v2': all(row['within_numeric_budgets_v2'] for row in rows if row['required']),
        'capacity': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--shared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'acceptance_revision': REVISION, 'limits': LIMITS,
        'rules_sha': os.environ.get('GITHUB_SHA'), 'p23_complete': False,
        'scope': 'Reassessment only; no new inference, Provider request or original report modification',
        'module': review(args.module, False), 'shared': review(args.shared, True)}
    assert report['module']['runtime_sha'] == report['shared']['runtime_sha']
    report['reassessment_complete'] = True
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key]['numeric_gate_passed_v2'] for key in ('module', 'shared')}))


if __name__ == '__main__':
    main()
