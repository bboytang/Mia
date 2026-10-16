"""Controlled fixture checks; not real app/model lifecycle acceptance."""

import asyncio
import json
from pathlib import Path
import sys
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.ci.mia_behavior_runtime import observe_hold
from server.companion import extraction
from server.companion.memory import MemoryError


class RuntimeHoldTests(unittest.IsolatedAsyncioTestCase):
    async def test_hold_preserves_validated_original_output_and_marks_only_actual_source(self):
        source = '我常用松纹刻刀做木雕'
        value = {'memories': [{'category': 'fact', 'content': source, 'source_quote': source,
            'source_index': 0, 'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False}]}
        calls = []

        async def resolve(scope):
            def extract(sources, context):
                calls.append(sources)
                return value
            return extract

        db = sqlite3.connect(':memory:', check_same_thread=False)
        self.addCleanup(db.close)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE mia_jobs (id TEXT, source_payload TEXT, owner TEXT, state TEXT)')
        db.execute('INSERT INTO mia_jobs VALUES (?,?,?,?)', ('synthetic-unit-job', json.dumps({'text': source}), 'synthetic-owner', 'extracting'))
        worker = SimpleNamespace(resolve=resolve, jobs=SimpleNamespace(store=SimpleNamespace(db=db, lock=threading.RLock())))
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {'mia_companion.extraction': extraction}):
            root = Path(directory)
            (root / 'shutdown-release.json').write_text('{}')
            report = {}
            observe_hold(worker, {'source': source}, root, report, threading.Lock(), lambda result: None)
            extract = await worker.resolve(SimpleNamespace(owner='synthetic-owner'))
            returned = await asyncio.to_thread(extract, [source], [])
            self.assertIs(returned, value)
            self.assertEqual(calls, [[source]])
            self.assertTrue(json.loads((root / 'shutdown-held.json').read_text())['validated_actual_output'])
            self.assertEqual(len(report['shutdown_held_outputs']), 1)
            self.assertEqual(report['shutdown_held_outputs'][0]['job_id'], 'synthetic-unit-job')

    async def test_invalid_output_never_gets_held_or_repaired(self):
        async def resolve(scope):
            return lambda sources, context: {'memories': [{'content': 'invented'}]}

        worker = SimpleNamespace(resolve=resolve)
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {'mia_companion.extraction': extraction}):
            root = Path(directory)
            report = {}
            observe_hold(worker, {'source': '我喜欢蓝色'}, root, report, threading.Lock(), lambda result: None)
            extract = await worker.resolve(None)
            with self.assertRaises(MemoryError):
                await asyncio.to_thread(extract, ['我喜欢蓝色'], [])
            self.assertFalse((root / 'shutdown-held.json').exists())
            self.assertEqual(report, {})
