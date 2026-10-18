import threading
import time
import unittest

from server.companion.model_requests import ModelRequestGate


class ModelRequestGateTests(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate():
            self.assertLess(time.monotonic(), deadline, 'Thread did not reach the requested gate state')
            time.sleep(.001)

    def test_two_active_foreground_fifo_precedes_background_and_release_is_idempotent(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=False), gate.acquire(foreground=True)]
        order, errors = [], []

        def run(label, foreground):
            try:
                with gate.acquire(foreground=foreground, timeout=2):
                    order.append(label)
                    if label == 'front-1':
                        raise ValueError('Provider stream failed')
            except ValueError:
                errors.append(label)

        threads = []
        for label, foreground in [('background', False), ('front-1', True), ('front-2', True)]:
            thread = threading.Thread(target=run, args=(label, foreground))
            threads.append(thread)
            thread.start()
            self.wait_for(lambda: sum(gate.snapshot()[key] for key in ('waiting_foreground', 'waiting_background')) == len(threads))
        self.assertEqual(gate.snapshot()['active'], 2)
        leases[0].release()
        for thread in threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())
        leases[0].release()
        leases[1].release()
        self.assertEqual(order, ['front-1', 'front-2', 'background'])
        self.assertEqual(errors, ['front-1'])
        self.assertEqual(gate.snapshot(), {'active': 0, 'waiting_foreground': 0, 'waiting_background': 0})

    def test_cancelled_native_waiter_cannot_start_after_its_outer_deadline(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        cancelled = threading.Event()
        entered, failures = [], []

        def run():
            try:
                with gate.acquire(foreground=False, cancelled=cancelled.is_set):
                    entered.append(True)
            except TimeoutError as error:
                failures.append(str(error))

        thread = threading.Thread(target=run)
        thread.start()
        self.wait_for(lambda: gate.snapshot()['waiting_background'] == 1)
        cancelled.set()
        leases[0].release()
        thread.join(2)
        leases[1].release()
        self.assertFalse(thread.is_alive())
        self.assertEqual(entered, [])
        self.assertEqual(failures, ['model_request_cancelled'])
        self.assertEqual(gate.snapshot()['active'], 0)

    def test_timeout_removes_waiter_without_releasing_running_streams(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=False)]
        try:
            with self.assertRaisesRegex(TimeoutError, 'model_request_queue_timeout'):
                gate.acquire(foreground=True, timeout=.01)
            self.assertEqual(gate.snapshot(), {'active': 2, 'waiting_foreground': 0, 'waiting_background': 0})
        finally:
            for lease in leases:
                lease.release()


if __name__ == '__main__':
    unittest.main()
