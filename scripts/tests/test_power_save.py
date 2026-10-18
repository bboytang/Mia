import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PowerSaveTests(unittest.TestCase):
    def test_actual_timer_handles_activity_after_dimming_and_screen_off(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = str(Path(temp) / 'power-save')
            subprocess.run([
                *shlex.split(os.environ.get('CXX', 'c++')), '-std=c++20', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT / 'scripts/tests/power_save_stubs'),
                '-I', str(ROOT / 'main/boards/common'),
                str(ROOT / 'main/boards/common/power_save_timer.cc'),
                str(ROOT / 'scripts/tests/power_save_driver.cc'), '-o', executable,
            ], check=True)
            subprocess.run([executable], check=True)
