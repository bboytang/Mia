import asyncio
import importlib.util
from pathlib import Path
import threading
import sqlite3
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('mia_stage_trace', Path(__file__).resolve().parents[1] / 'mia_stage_trace.py')
trace_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace_module)


class StageTraceTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_origin_nested_spans_threads_and_clipping(self):
        clock = [100.0]
        trace = trace_module.StageTrace({'started': 100.0, 'first_sentence_ms': 900}, clock=lambda: clock[0])
        with trace.span('request'):
            clock[0] = 100.2
            with trace.span('prepare'):
                clock[0] = 100.4
                await asyncio.to_thread(lambda: None)
            clock[0] = 100.9
            with trace.span('deliver'):
                clock[0] = 101.0
        report = trace.report()
        self.assertEqual(report['dropped'], 0)
        stages = report['whole_case']
        self.assertAlmostEqual(stages['request']['inclusive_ms'], 1000)
        self.assertAlmostEqual(stages['request']['exclusive_ms'], 700)
        self.assertAlmostEqual(report['before_tts_ready']['request']['inclusive_ms'], 900)
        self.assertAlmostEqual(report['events'][1]['start_ms'], 200)

    async def test_wrappers_preserve_values_errors_cancellation_and_restore(self):
        target = SimpleNamespace()
        def call():
            raise ValueError('never store this private body')
        async def async_call():
            raise asyncio.CancelledError()
        target.call, target.async_call = call, async_call
        trace = trace_module.StageTrace({'started': 0})
        trace.wrap(target, 'call', 'sync')
        trace.wrap(target, 'async_call', 'async')
        with self.assertRaises(ValueError):
            target.call()
        with self.assertRaises(asyncio.CancelledError):
            await target.async_call()
        trace.close()
        self.assertIs(target.call, call)
        self.assertIs(target.async_call, async_call)
        self.assertEqual([x['error_class'] for x in trace.events], ['ValueError', 'CancelledError'])
        self.assertNotIn('private', str(trace.report()))

    async def test_lock_is_reentrant_and_capacity_is_bounded(self):
        trace = trace_module.StageTrace({'started': 0}, capacity=1)
        original = threading.RLock()
        lock = trace_module.ObservedLock(original, trace)
        with lock:
            with lock:
                self.assertTrue(original._is_owned())
        self.assertFalse(original._is_owned())
        self.assertEqual(len(trace.events), 1)
        self.assertEqual(trace.dropped, 1)
        trace.close()
        with trace.span('disabled'):
            pass
        self.assertEqual(trace.dropped, 1)

    async def test_overlapping_children_are_counted_as_union_not_double_subtracted(self):
        trace = trace_module.StageTrace({'started': 0})
        trace.events = [dict(id=1, parent=None, name='all', start=0, end=1, error_class=None),
            dict(id=2, parent=1, name='a', start=.1, end=.6, error_class=None),
            dict(id=3, parent=1, name='b', start=.3, end=.8, error_class=None)]
        self.assertAlmostEqual(trace.summary()['all']['exclusive_ms'], 300)

    async def test_sqlite_proxy_preserves_cursor_transaction_and_rollback(self):
        trace = trace_module.StageTrace({'started': 0})
        original = sqlite3.connect(':memory:')
        db = trace_module.ObservedDB(original, trace)
        try:
            db.execute('CREATE TABLE test(value TEXT)')
            with self.assertRaises(ValueError), db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO test VALUES (?)', ('private synthetic value',))
                raise ValueError()
            self.assertEqual(db.execute('SELECT COUNT(*) FROM test').fetchone()[0], 0)
            self.assertEqual([x['name'] for x in trace.events], ['sqlite.begin_wait_and_execute'])
            self.assertNotIn('private', str(trace.report()))
        finally:
            original.close()
