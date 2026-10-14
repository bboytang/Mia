"""Check or apply five official fixes to a source copy; never restart services."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='xiaozhi-esp32-server source root')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.source.resolve()
    bundle = Path(__file__).resolve().parent
    manifest = json.loads((bundle / 'files.json').read_text())
    for name, hashes in manifest['files'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != hashes['before']:
            raise SystemExit(f'Refusing changed source; review customizations: {name}')
    patch = str(bundle / 'official.patch')
    subprocess.run(['git', 'apply', '--check', patch], cwd=root, check=True)
    if args.apply:
        subprocess.run(['git', 'apply', patch], cwd=root, check=True)
        for name, hashes in manifest['files'].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != hashes['after']:
                raise SystemExit(f'Applied source does not match official commit: {name}')
        print(f'Applied five official fixes from {manifest["official"]}; services untouched')
    else:
        print('All five files match the audited baseline; no files changed')


if __name__ == '__main__':
    main()
