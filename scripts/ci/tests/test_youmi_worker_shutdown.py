import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('youmi_worker_shutdown',
    Path(__file__).resolve().parents[1] / 'youmi_worker_shutdown.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ShutdownRecoveryEvidenceTests(unittest.TestCase):
    def test_recovery_guard_counts_and_blocks_sdk_before_any_request(self):
        calls, saves = [], []
        sdk = SimpleNamespace(create=lambda **kwargs: calls.append(kwargs))
        llm = SimpleNamespace(create_instance=lambda *args, **kwargs:
            SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=sdk))))
        report = {'provider_requests': 0}
        with patch.dict(sys.modules, {'core': SimpleNamespace(utils=SimpleNamespace(llm=llm)),
                'core.utils': SimpleNamespace(llm=llm), 'core.utils.llm': llm}):
            probe.guard_recovery_provider(report, lambda value: saves.append(dict(value)))
            self.assertTrue(report['recovery_guard_before_launch'])
            self.assertEqual(report['provider_requests'], 0)
            provider = llm.create_instance('openai', {})
            with self.assertRaisesRegex(AssertionError, 'another model request'):
                provider.client.chat.completions.create(model='isolated-test')
        self.assertFalse(calls)
        self.assertTrue(report['recovery_repeated_sdk'])
        self.assertEqual(report['provider_requests'], 1)
        self.assertEqual(len(saves), 2)

    def test_checkpoint_is_read_only_and_distinguishes_durable_and_cleared_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app-child').mkdir()
            path = root / 'app-child/memory.sqlite3'
            with sqlite3.connect(path) as db:
                db.executescript('CREATE TABLE mia_jobs(id,owner,state,attempts,validated_result);'
                    'CREATE TABLE memories(id,owner,content,confirmed);'
                    'CREATE TABLE sources(memory_id,session_id,excerpt);'
                    'CREATE TABLE mia_vectors(memory_id,dimension,normalized_vector);')
                db.execute('INSERT INTO mia_jobs VALUES (?,?,?,?,?)', ('job','owned','validated',1,'{"_schema":1}'))
            before = path.read_bytes()
            value = probe.checkpoint(root, 'job')
            self.assertTrue(value['validated_sha256'])
            self.assertEqual(value['facts'], [])
            self.assertEqual(path.read_bytes(), before)
            with sqlite3.connect(path) as db:
                db.execute("UPDATE mia_jobs SET validated_result=NULL,state='committed'")
            self.assertIsNone(probe.checkpoint(root, 'job')['validated_sha256'])
            with sqlite3.connect(path) as db:
                db.execute("UPDATE mia_jobs SET validated_result='{}',state='validated'")
            with self.assertRaises(KeyError):
                probe.checkpoint(root, 'job')

    def test_recovery_cannot_pass_with_same_process_or_repeated_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app-child').mkdir()
            report = {'inflight_shutdown': {'pid': 111, 'checkpoint': {'id': 'job'}}}
            for child in ({'pid': 111}, {'pid': 222, 'recovery_guard_before_launch': True,
                    'recovery_repeated_sdk': True}):
                (root / 'app-child/app-results.json').write_text(json.dumps(child))
                with self.subTest(child=child), patch.dict(probe.os.environ, {'MIA_P23_SHUTDOWN_STAGE': 'recover'}), \
                        patch.object(probe, 'checkpoint', return_value={}):
                    with self.assertRaises(AssertionError):
                        probe.after_exit(root, report, lambda value: self.fail('Invalid evidence persisted as success'))


if __name__ == '__main__':
    unittest.main()
