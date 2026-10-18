import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MiaSimplifiedTests(unittest.TestCase):
    def test_real_dictionary_and_firmware_utf8_conversion(self):
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([
                sys.executable, str(ROOT / 'scripts/passport/generate_simplified.py'),
                str(ROOT / 'third_party/opencc'), str(Path(temp) / 'mia_simplified_dictionary.h'),
            ], check=True)
            executable = str(Path(temp) / 'mia-simplified')
            subprocess.run([
                *shlex.split(os.environ.get('CXX', 'c++')), '-std=c++17',
                '-Wall', '-Wextra', '-Werror', '-I', temp,
                '-I', str(ROOT / 'main/boards/folotoy/ai-passport'),
                str(ROOT / 'scripts/tests/mia_simplified_driver.cc'), '-o', executable,
            ], check=True)
            subprocess.run([executable], check=True)
