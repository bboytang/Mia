"""Apply the responsive changes to a verified copy of upstream manager-web.

This operates on source only. It never builds, restarts, or deploys a service.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tempfile


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
    private_patch = str(bundle / 'private-authorization.patch')
    settings_patch = str(bundle / 'companion-settings.patch')
    with tempfile.TemporaryDirectory(prefix='mia-admin-check-') as scratch:
        for relative in manifest['files']:
            source = root / relative
            if source.is_file():
                target = Path(scratch) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        for candidate in (desktop_patch, patch, private_patch, settings_patch):
            subprocess.run(['git', 'apply', '--unidiff-zero', '--check', candidate], cwd=scratch, check=True)
            subprocess.run(['git', 'apply', '--unidiff-zero', candidate], cwd=scratch, check=True)
    if args.apply:
        subprocess.run(['git', 'apply', '--unidiff-zero', desktop_patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', '--check', patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', '--check', private_patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', private_patch], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--unidiff-zero', settings_patch], cwd=root, check=True)
        shutil.copy2(bundle / 'MiaSettingsDialog.vue', root / 'main/manager-web/src/components/MiaSettingsDialog.vue')
        print(f'Applied responsive source changes for upstream {manifest["commit"]}')
    else:
        print(f'All source checks passed for upstream {manifest["commit"]}; no files changed')


if __name__ == '__main__':
    main()
