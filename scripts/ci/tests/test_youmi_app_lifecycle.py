import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


class AppLifecycleFinalizerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, MIA_P23_REPORT_DIR=self.directory.name):
            spec = importlib.util.spec_from_file_location('mia_app_lifecycle',
                Path(__file__).resolve().parents[1] / 'verify_youmi_app_lifecycle.py')
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
        self.path = Path(self.directory.name) / 'app-lifecycle-results.json'
        (Path(self.directory.name) / 'container-stopped.txt').write_text(
            '/youmip23-mysql 0 false false\n/youmip23-redis 0 false false\n')

    def tearDown(self):
        self.directory.cleanup()

    def report(self):
        return {'app_lifecycle_preflight_passed': True, 'p23_complete': False,
            'shutdown_signal_monotonic': time.monotonic(),
            'members_ready': {role: {'pid': 1073741824 + i, 'start_ticks': '0'}
                for i, role in enumerate(('python', 'harness', 'manager', 'mysql', 'redis'))}}

    def test_live_database_prevents_success_even_after_app_exit(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            ticks = (Path('/proc') / str(process.pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]
            report = self.report()
            report['members_ready']['mysql'] = {'pid': process.pid, 'start_ticks': ticks}
            self.path.write_text(json.dumps(report))
            with self.assertRaises(SystemExit):
                self.module.finalize()
            result = json.loads(self.path.read_text())
            self.assertEqual(result['idle_service_group_shutdown']['remaining_original_processes'], ['mysql'])
            self.assertTrue(result['app_lifecycle_preflight_passed'])
        finally:
            process.terminate()
            process.wait(timeout=3)
        self.module.finalize()
        self.assertTrue(json.loads(self.path.read_text())['idle_service_group_shutdown']['passed'])

    def test_shutdown_budget_includes_time_after_app_process_exit(self):
        report = self.report()
        report['app_process_shutdown_seconds'] = .1
        report['shutdown_signal_monotonic'] = 100
        self.path.write_text(json.dumps(report))
        with patch.object(self.module.time, 'monotonic', return_value=120.001):
            with self.assertRaises(SystemExit):
                self.module.finalize()
        result = json.loads(self.path.read_text())
        self.assertFalse(result['idle_service_group_shutdown']['passed'])
        self.assertEqual(result['idle_service_group_shutdown']['remaining_original_processes'], [])
        self.assertFalse(result['p23_complete'])

    def test_forced_database_exit_cannot_count_as_clean_shutdown(self):
        self.path.write_text(json.dumps(self.report()))
        (Path(self.directory.name) / 'container-stopped.txt').write_text(
            '/youmip23-mysql 137 false false\n/youmip23-redis 0 false false\n')
        with self.assertRaises(SystemExit):
            self.module.finalize()
        self.assertFalse(json.loads(self.path.read_text())['idle_service_group_shutdown']['passed'])


if __name__ == '__main__':
    unittest.main()
