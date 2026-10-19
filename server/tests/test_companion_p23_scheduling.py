"""Controlled P23 scheduling counterexamples; never invoke a remote model."""

import asyncio
import threading
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from server.companion.jobs import JobStore, MemoryWorker
from server.companion.extraction import LLMMemoryExtractor
from server.companion.model_requests import ModelQueueError, ModelRequestGate
from server.tests import test_companion_jobs as fixtures


RECORDS = []


class GateCounterexamples(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            self.assertLess(time.monotonic(), deadline, 'Controlled gate state not reached')
            time.sleep(.001)

    def test_elapsed_waiter_cannot_take_newly_available_slot(self):
        gate = ModelRequestGate()
        gate.active = 2
        clock = [0.0]
        def release_after_deadline(unused):
            clock[0] = 30.001
            gate.active = 1
        with patch('server.companion.model_requests.time.monotonic', side_effect=lambda: clock[0]), \
                patch.object(gate.condition, 'wait', side_effect=release_after_deadline):
            with self.assertRaisesRegex(ModelQueueError, 'model_request_queue_timeout'):
                gate.acquire(foreground=False, timeout=30)
        self.assertEqual(gate.snapshot(), {'active': 1, 'waiting_foreground': 0, 'waiting_background': 0})
        RECORDS.append({'case': 'expired_gate_waiter', 'virtual_queue_ms': 30001,
            'sdk_calls': 0, 'gate': gate.snapshot()})

    def test_bounded_rolling_foreground_precedes_background_then_drains(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        entered, errors, snapshots = [], [], []
        release = [threading.Event() for _ in range(6)]
        background_done = threading.Event()
        def background():
            try:
                with gate.acquire(foreground=False, timeout=5):
                    entered.append('background')
                    background_done.set()
            except Exception as error:
                errors.append(type(error).__name__)
        def foreground(index):
            try:
                with gate.acquire(foreground=True, timeout=5):
                    entered.append('front-' + str(index))
                    if not release[index].wait(5):
                        errors.append('control_timeout')
            except Exception as error:
                errors.append(type(error).__name__)
        threads = [threading.Thread(target=background)]
        threads[0].start()
        self.wait_for(lambda: gate.snapshot()['waiting_background'] == 1)
        def enqueue(index):
            thread = threading.Thread(target=foreground, args=(index,))
            threads.append(thread)
            thread.start()
            self.wait_for(lambda: gate.snapshot()['waiting_foreground'] == 1)
        try:
            enqueue(0)
            leases[0].release()
            for index in range(6):
                self.wait_for(lambda: 'front-' + str(index) in entered)
                snapshots.append(gate.snapshot())
                self.assertFalse(background_done.is_set())
                self.assertEqual(gate.snapshot()['active'], 2)
                if index < 5:
                    enqueue(index + 1)
                release[index].set()
            self.assertTrue(background_done.wait(3))
        finally:
            for signal in release:
                signal.set()
            for lease in leases:
                lease.release()
            for thread in threads:
                thread.join(6)
                self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(entered, ['front-' + str(i) for i in range(6)] + ['background'])
        RECORDS.append({'case': 'bounded_rolling_foreground', 'initial_active_foreground': 2,
            'admission_order': entered, 'snapshots_before_release': snapshots,
            'background_served_only_after_foreground_waiters_drain': True,
            'scope': 'Finite controlled arrivals, not an unbounded-load guarantee'})

    def test_full_queue_and_cancel_never_release_active_native_calls(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        try:
            gate.foreground.extend(object() for _ in range(128))
            with self.assertRaisesRegex(ModelQueueError, 'queue_full'):
                gate.acquire(foreground=False)
            gate.foreground.clear()
            with self.assertRaisesRegex(ModelQueueError, 'cancelled'):
                gate.acquire(foreground=False, cancelled=lambda: True)
            self.assertEqual(gate.snapshot()['active'], 2)
            RECORDS.append({'case': 'queue_bound_cancel', 'bound': 128, 'sdk_calls': 0,
                'gate_before_native_completion': gate.snapshot()})
        finally:
            for lease in leases:
                lease.release()


class WorkerCounterexamples(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.JobTests.setUp
    tearDown = fixtures.JobTests.tearDown
    event = fixtures.JobTests.event
    row = fixtures.JobTests.row

    async def test_expiry_during_preparation_starts_no_attempt_or_sdk(self):
        async def resolve(scope):
            self.now[0] = 221
            return lambda sources, context: self.calls.append('SDK') or {'memories': []}
        self.worker.resolve = resolve
        admitted = await self.worker.submit(self.event())
        await self.worker.run_once()
        row = self.row(admitted)
        self.assertEqual(self.calls, [])
        self.assertEqual((row['state'], row['attempts'], row['error_category']), ('failed', 0, 'deadline_exceeded'))
        RECORDS.append({'case': 'expiry_in_preparation', 'job_created': 100, 'deadline': 220,
            'clock_before_attempt': 221, 'sdk_calls': 0, 'attempts': row['attempts'], 'state': row['state']})

    async def test_queued_attempt_survives_restart_without_refund_or_third_attempt(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        provider = SimpleNamespace(response_no_stream=Mock(return_value='{"memories":[]}'))
        async def resolve(scope):
            return LLMMemoryExtractor(lambda: provider)
        self.worker.resolve = resolve
        self.worker.extraction_timeout = .02
        with patch('server.companion.extraction.model_requests', gate):
            try:
                admitted = await self.worker.submit(self.event())
                await self.worker.run_once()
                before = self.row(admitted)
                self.assertEqual((before['attempts'], before['error_category']), (1, 'model_queue_timeout'))
                self.assertEqual(provider.response_no_stream.call_count, 0)
            finally:
                for lease in leases:
                    lease.release()
            deadline = time.monotonic() + 3
            while not self.worker.lane.done.is_set():
                self.assertLess(time.monotonic(), deadline)
                await asyncio.sleep(.001)
            self.jobs = JobStore(self.store, policy_version=1)
            self.jobs.recover()
            self.now[0] += 2
            self.worker = MemoryWorker(self.jobs, self.policy, resolve, encoder=self.encoder)
            await self.worker.run_once()
            after = self.row(admitted)
            self.assertEqual((after['state'], after['attempts']), ('empty', 2))
            self.assertEqual(provider.response_no_stream.call_count, 1)
            self.assertFalse(await self.worker.run_once())
            RECORDS.append({'case': 'queued_attempt_restart', 'first_attempt_phase': 'model_slot_queue',
                'before': {k: before[k] for k in ('state','attempts','error_category')},
                'after': {k: after[k] for k in ('state','attempts','error_category')},
                'actual_mock_sdk_calls': provider.response_no_stream.call_count,
                'attempt_policy_change': 'Not implemented; requires approval'})

    async def test_continuous_foreground_expires_background_without_sdk(self):
        admitted = await self.worker.submit(self.event())
        self.worker.foreground = 2
        for now in (101, 150, 219):
            self.now[0] = now
            self.assertFalse(await self.worker.run_once())
        self.assertEqual(self.row(admitted)['attempts'], 0)
        self.now[0] = 220
        await self.worker.run_once()
        row = self.row(admitted)
        self.assertEqual((row['state'], row['attempts']), ('failed', 0))
        self.assertEqual(self.calls, [])
        RECORDS.append({'case': 'foreground_blocks_until_deadline', 'foreground': 2,
            'virtual_queue_seconds': 120, 'sdk_calls': 0, 'attempts': 0, 'terminal': row['error_category'],
            'liveness': 'No unconditional background guarantee under saturated foreground'})

    async def test_queue_near_lifetime_expiry_keeps_original_attempt_accounting(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        provider = SimpleNamespace(response_no_stream=Mock(return_value='{"memories":[]}'))
        async def resolve(scope):
            return LLMMemoryExtractor(lambda: provider)
        self.worker.resolve = resolve
        self.worker.extraction_timeout = .02
        admitted = await self.worker.submit(self.event())
        self.now[0] = 219
        with patch('server.companion.extraction.model_requests', gate):
            try:
                await self.worker.run_once()
                queued = self.row(admitted)
                self.assertEqual((queued['attempts'], queued['error_category']), (1, 'model_queue_timeout'))
                self.now[0] = 220
                await self.worker.run_once()
                self.assertEqual((self.row(admitted)['state'], self.row(admitted)['attempts']), ('failed', 1))
            finally:
                for lease in leases:
                    lease.release()
            deadline = time.monotonic() + 3
            while not self.worker.lane.done.is_set():
                self.assertLess(time.monotonic(), deadline)
                await asyncio.sleep(.001)
        self.assertEqual(provider.response_no_stream.call_count, 0)
        RECORDS.append({'case': 'queue_near_120_second_deadline', 'job_age_at_queue_seconds': 119,
            'controlled_per_attempt_timeout_seconds': .02, 'attempts': 1, 'actual_mock_sdk_calls': 0,
            'final': 'deadline_exceeded', 'original_attempt_semantics_preserved': True})

    async def test_generation_and_validation_failures_count_real_entries_separately(self):
        for phase in ('generation', 'validation'):
            calls = []
            class Provider:
                def response_no_stream(self, *unused):
                    calls.append(True)
                    if phase == 'generation':
                        raise RuntimeError('synthetic Provider error')
                    return 'not JSON'
            async def resolve(scope):
                return LLMMemoryExtractor(Provider)
            self.worker.resolve = resolve
            admitted = await self.worker.submit(self.event(phase))
            await self.worker.run_once()
            row = self.row(admitted)
            category = 'provider' if phase == 'generation' else 'parse'
            self.assertEqual((row['attempts'], row['error_category']), (1, category))
            self.assertEqual(len(calls), 1)
            RECORDS.append({'case': phase + '_failure', 'actual_mock_sdk_calls': len(calls),
                'attempts': row['attempts'], 'error_category': category})
