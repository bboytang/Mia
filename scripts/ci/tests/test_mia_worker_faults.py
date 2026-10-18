import importlib.util
from pathlib import Path
import sqlite3
import sys
import unittest


directory = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(directory))
try:
    spec = importlib.util.spec_from_file_location('mia_worker_faults', directory / 'mia_worker_faults.py')
    faults = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(faults)
finally:
    sys.path.pop(0)


class ActualSQLiteWriteRefusalTests(unittest.TestCase):
    def test_cached_fact_insert_is_refused_without_blocking_durable_job_update_or_recovery(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE memories(content TEXT)')
        db.execute('CREATE TABLE mia_jobs(state TEXT,validated_result TEXT)')
        db.execute("INSERT INTO mia_jobs VALUES ('validated','original-result')")
        insert = 'INSERT INTO memories VALUES (?)'
        db.execute(insert, ('existing',))
        db.commit()
        db.set_authorizer(faults.reject_fact_insert)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute(insert, ('refused',))
        db.rollback()
        db.execute("UPDATE mia_jobs SET state='retry_wait'")
        self.assertEqual(db.execute('SELECT state,validated_result FROM mia_jobs').fetchone(),
            ('retry_wait', 'original-result'))
        db.set_authorizer(None)
        db.execute(insert, ('recovered',))
        self.assertEqual(db.execute('SELECT content FROM memories').fetchall(), [('existing',), ('recovered',)])


if __name__ == '__main__':
    unittest.main()
