"""Apply the responsive changes to a verified copy of upstream manager-web.

This operates on source only. It never builds, restarts, or deploys a service.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='xiaozhi-esp32-server source root')
    parser.add_argument('--apply', action='store_true', help='apply after all checks pass')
    args = parser.parse_args()
    root = args.source.resolve()
    bundle = Path(__file__).resolve().parent
    manifest = json.loads((bundle / 'upstream-files.json').read_text())
    for relative, expected in manifest['files'].items():
        path = root / relative
        if expected is None:
            if path.exists():
                raise SystemExit(f'Refusing to overwrite existing file: {relative}')
        elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Upstream file differs; review custom changes first: {relative}')
    desktop_patch = str(bundle / 'production-dialogs.patch')
    patch = str(bundle / 'responsive.patch')
    subprocess.run(['git', 'apply', '--unidiff-zero', '--check', desktop_patch], cwd=root, check=True)
    subprocess.run(['git', 'apply', '--unidiff-zero', '--check', patch], cwd=root, check=True)
    if args.apply:
        subprocess.run(['git', 'apply', '--unidiff-zero', desktop_patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', '--check', patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', patch], cwd=root, check=True)
        print(f'Applied responsive source changes for upstream {manifest["commit"]}')
    else:
        print(f'All source checks passed for upstream {manifest["commit"]}; no files changed')


if __name__ == '__main__':
    main()
