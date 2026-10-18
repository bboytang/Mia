import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PassportUpdateTests(unittest.TestCase):
    def test_actual_signed_updater_under_faults(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            fixture = json.loads((ROOT / 'scripts/tests/fixtures/passport_capsule.json').read_text())
            (path / 'capsule').write_bytes(base64.b64decode(fixture['capsule']))
            (path / 'table').write_bytes(base64.b64decode(fixture['table']))
            sources = [ROOT / 'main/passport' / name for name in ('capsule.cc', 'crypto_psa.cc', 'signed_update.cc')]
            command = [*shlex.split(os.environ.get('CXX', 'c++')), '-std=c++20', '-Wall', '-Wextra', '-Werror',
                       '-Wno-unused-parameter', '-I', str(ROOT / 'scripts/tests/passport_stubs'),
                       '-I', str(ROOT / 'main/passport'), *(str(p) for p in sources),
                       str(ROOT / 'scripts/tests/passport_update_driver.cc'), '-lcrypto', '-o', str(path / 'test')]
            subprocess.run(command, check=True)
            subprocess.run([str(path / 'test'), str(path / 'capsule'), str(path / 'table')], check=True)
