"""Process-wide model request slots; foreground FIFO precedes background FIFO."""

from collections import deque
import threading
import time


class ModelQueueError(TimeoutError):
    def __init__(self, reason):
        super().__init__(reason)
        self.category = {'model_request_cancelled': 'cancelled',
            'model_request_queue_full': 'model_queue_full',
            'model_request_queue_timeout': 'model_queue_timeout'}[reason]


class Lease:
    def __init__(self, gate):
        self.gate = gate
        self.released = False

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.release()

    def release(self):
        with self.gate.condition:
            if not self.released:
                self.released = True
                self.gate.active -= 1
                self.gate.condition.notify_all()


class ModelRequestGate:
    def __init__(self):
        self.condition = threading.Condition()
        self.active = 0
        self.foreground = deque()
        self.background = deque()

    def snapshot(self):
        with self.condition:
            return {'active': self.active, 'waiting_foreground': len(self.foreground),
                'waiting_background': len(self.background)}

    def acquire(self, *, foreground, cancelled=lambda: False, timeout=30):
        deadline = time.monotonic() + timeout
        ticket = object()
        queue = self.foreground if foreground else self.background
        with self.condition:
            if len(self.foreground) + len(self.background) >= 128:
                raise ModelQueueError('model_request_queue_full')
            queue.append(ticket)
            try:
                while True:
                    if cancelled():
                        raise ModelQueueError('model_request_cancelled')
                    preferred = self.foreground if self.foreground else self.background
                    if self.active < 2 and preferred is queue and queue[0] is ticket:
                        queue.popleft()
                        self.active += 1
                        self.condition.notify_all()
                        return Lease(self)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ModelQueueError('model_request_queue_timeout')
                    self.condition.wait(min(.05, remaining))
            finally:
                if ticket in queue:
                    queue.remove(ticket)
                    self.condition.notify_all()


model_requests = ModelRequestGate()
