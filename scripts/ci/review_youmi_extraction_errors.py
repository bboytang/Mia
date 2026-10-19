"""Read-only replay of captured synthetic failures, never a real task verdict."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.companion.extraction import validate_output
from server.companion.proposal import ExtractionError


def review(root):
    source = root / 'performance-worker-fairness-complete-child.json.gz'
    raw = gzip.decompress(source.read_bytes())
    child = json.loads(raw)
    baseline = json.loads((root / 'performance-trailing-fence-offline.json').read_text())
    expected = {(x['job_id'], x['attempt']): x for x in baseline['cases']}
    report = {'source_run': 39178747148, 'source_raw_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Offline original failures only, empty prior context; no requests, writes or retrospective task-success verdict.',
        'baseline': 'performance-trailing-fence-offline.json (ca03844 format compatibility)', 'cases': []}
    for failure in child['validation_failures']:
        value = failure['original_output']
        before = json.dumps(value, ensure_ascii=False).encode()
        assert hashlib.sha256(before).hexdigest() == failure['original_output_sha256']
        row = {k: failure[k] for k in ('job_id', 'attempt', 'original_output_sha256')}
        try:
            validate_output(value, failure['sources'], [])
            row.update(accepted_in_empty_context=True, category='accepted')
        except ExtractionError as error:
            row.update(accepted_in_empty_context=False, category=error.category, code=error.code)
        old = expected[(failure['job_id'], failure['attempt'])].get('source_validation_empty_context_passed', False)
        assert row['accepted_in_empty_context'] == old
        assert json.dumps(value, ensure_ascii=False).encode() == before
        report['cases'].append(row)
    report['all_verdicts_and_original_outputs_unchanged'] = True
    report['counts'] = dict(Counter(x['category'] for x in report['cases']))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite evidence')
    args.output.write_text(json.dumps(review(args.evidence_dir), ensure_ascii=False, indent=2) + '\n')
