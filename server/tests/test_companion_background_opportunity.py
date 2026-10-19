"""Deterministic bounded opportunity schedules; no model or remote traffic."""
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from server.companion.model_requests import ModelRequestGate


RECORDS = []


class BackgroundOpportunityTests(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            self.assertLess(time.monotonic(), deadline, 'Gate control failed')
            time.sleep(.001)

    def schedule(self, burst, age):
        clock = [0]
        gate = ModelRequestGate(background_after=age, foreground_burst=burst)
        order, failures, releases, threads = [], [], {}, []
        def run(label, front):
            try:
                with gate.acquire(foreground=front, timeout=100):
                    order.append(label)
                    if not releases[label].wait(3):
                        failures.append('controlled_release_missing')
            except Exception as error:
                failures.append(type(error).__name__)
        def enqueue(label, front):
            releases[label] = threading.Event()
            thread = threading.Thread(target=run, args=(label, front))
            threads.append(thread)
            thread.start()
        with patch('server.companion.model_requests.time', SimpleNamespace(monotonic=lambda: clock[0])):
            held = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
            try:
                enqueue('background', False)
                self.wait_for(lambda: gate.snapshot()['waiting_background'] == 1)
                enqueue('front-0', True)
                self.wait_for(lambda: gate.snapshot()['waiting_foreground'] == 1)
                clock[0] = age
                held[0].release()
                for index in range(burst):
                    self.wait_for(lambda: f'front-{index}' in order)
                    self.assertNotIn('background', order)
                    self.assertEqual(gate.snapshot()['active'], 2)
                    enqueue(f'front-{index + 1}', True)
                    self.wait_for(lambda: gate.snapshot()['waiting_foreground'] == 1)
                    releases[f'front-{index}'].set()
                self.wait_for(lambda: 'background' in order)
                self.assertEqual(order, [f'front-{n}' for n in range(burst)] + ['background'])
                self.assertEqual(gate.snapshot()['waiting_foreground'], 1)
                self.assertEqual(gate.snapshot()['active'], 2)
                # Already running front-2nd-slot is never preempted. Releasing
                # it admits the next foreground even while background runs.
                held[1].release()
                self.wait_for(lambda: f'front-{burst}' in order)
            finally:
                for event in releases.values():
                    event.set()
                for lease in held:
                    lease.release()
                for thread in threads:
                    thread.join(4)
                    self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(gate.snapshot()['active'], 0)
        RECORDS.append({'foreground_burst': burst, 'background_after_seconds': age,
            'controlled_clock_seconds': clock[0], 'order': order, 'remaining': gate.snapshot(),
            'scope': 'Virtual age, real threaded gate; no claim about provider completion time'})

    def test_candidate_four_grants_ten_seconds(self):
        self.schedule(4, 10)

    def test_candidate_eight_grants_twenty_seconds(self):
        self.schedule(8, 20)

    def test_foreground_first_background_first_and_age_both_required(self):
        gate = ModelRequestGate(background_after=10, foreground_burst=4)
        # Uncontended requests do not wait for an unnecessary quota.
        with gate.acquire(foreground=False):
            self.assertEqual(gate.active, 1)
            with gate.acquire(foreground=True):
                self.assertEqual(gate.active, 2)
        self.assertEqual(gate.active, 0)
        self.assertEqual(gate.background_active, 0)

    def test_second_background_cannot_take_foreground_slot_and_cancellation_cleans_queue(self):
        gate = ModelRequestGate(background_after=10, foreground_burst=4)
        held = gate.acquire(foreground=False)
        cancelled = threading.Event()
        failures = []
        def background():
            try:
                with gate.acquire(foreground=False, cancelled=cancelled.is_set):
                    failures.append('second_background_started')
            except TimeoutError as error:
                failures.append(str(error))
        thread = threading.Thread(target=background)
        thread.start()
        try:
            self.wait_for(lambda: gate.snapshot()['waiting_background'] == 1)
            with gate.acquire(foreground=True):
                self.assertEqual(gate.active, 2)
                self.assertEqual(gate.background_active, 1)
            cancelled.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(gate.active, 1)
        finally:
            cancelled.set()
            held.release()
            thread.join(2)
        self.assertEqual(failures, ['model_request_cancelled'])


if __name__ == '__main__':
    unittest.main()
