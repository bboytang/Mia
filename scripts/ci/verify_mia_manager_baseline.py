"""Compare CI-built manager classes with the read-only P03 deployment baseline."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--classes', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    rows = {}
    for name, expected in baseline['classes'].items():
        path = args.classes / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        rows[name] = {'expected': expected, 'actual': actual, 'matches': actual == expected}
    report = {'code_sha': os.environ.get('GITHUB_SHA'),
              'upstream_sha': '87c6df77b0220ddbd8fc804f984f83f69f3225e5',
              'classes': rows, 'matches': all(row['matches'] for row in rows.values()),
              'note': 'Build reproducibility only; does not prove credential issuance or authorization.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['matches']:
        raise SystemExit('Manager baseline mismatch: inspect before changing production hooks')


if __name__ == '__main__':
    main()
