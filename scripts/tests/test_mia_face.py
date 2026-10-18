import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MiaFaceTests(unittest.TestCase):
    def test_firmware_animation_geometry_and_emotion_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = str(Path(temp) / 'mia-face')
            subprocess.run([
                *shlex.split(os.environ.get('CXX', 'c++')), '-std=c++17',
                '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT / 'main/boards/folotoy/ai-passport'),
                str(ROOT / 'scripts/tests/mia_face_driver.cc'), '-o', executable,
            ], check=True)
            subprocess.run([executable], check=True)
