import importlib.util
import json
from pathlib import Path
import sqlite3
import threading
from types import SimpleNamespace
import unittest

from server.companion.extraction import source_supported


spec = importlib.util.spec_from_file_location('mia_worker_competition',
    Path(__file__).resolve().parents[1] / 'mia_worker_competition.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ExtractionBindingTests(unittest.TestCase):
    def test_pending_foreign_and_ambiguous_rows_cannot_prove_sdk_job_binding(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE mia_jobs(id TEXT,owner TEXT,state TEXT,source_payload TEXT,attempts INTEGER)')
        worker = SimpleNamespace(jobs=SimpleNamespace(store=SimpleNamespace(db=db, lock=threading.RLock())))
        owner, source = 'user:1:agent:a', probe.SOURCE

        def insert(key, scope, state, text):
            db.execute('INSERT INTO mia_jobs VALUES (?,?,?,?,1)',
                (key, scope, state, json.dumps({'text': text})))

        insert('pending', owner, 'pending', source)
        insert('foreign', 'user:2:agent:a', 'extracting', source)
        insert('other-source', owner, 'extracting', '我在周日整理其他物品')
        with self.assertRaises(AssertionError):
            probe.active_job(worker, owner, [source])
        insert('actual', owner, 'extracting', source)
        self.assertEqual(probe.active_job(worker, owner, [source])['job_id'], 'actual')
        insert('ambiguous', owner, 'extracting', source)
        with self.assertRaises(AssertionError):
            probe.active_job(worker, owner, [source])

    def test_new_probe_source_cannot_take_question_empty_shortcut(self):
        self.assertTrue(source_supported(probe.SOURCE, None))
        self.assertTrue(source_supported(probe.SOURCE, probe.SOURCE))
        self.assertFalse(source_supported('周三的钢琴练习安排是什么？', None))


if __name__ == '__main__':
    unittest.main()
