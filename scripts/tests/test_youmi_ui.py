import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class YoumiUiTests(unittest.TestCase):
    def test_three_button_character_coverage_and_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = str(Path(temp) / 'youmi-ui')
            subprocess.run([
                *shlex.split(os.environ.get('CXX', 'c++')), '-std=c++17',
                '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                '-I', str(ROOT / 'main/boards/folotoy/ai-passport'),
                str(ROOT / 'scripts/tests/youmi_ui_driver.cc'), '-o', executable,
            ], check=True)
            subprocess.run([executable], check=True)
