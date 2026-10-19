"""Two model slots; foreground FIFO with one bounded background opportunity."""

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
    def __init__(self, gate, foreground):
        self.gate = gate
        self.foreground = foreground
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
                if not self.foreground:
                    self.gate.background_active -= 1
                self.gate.condition.notify_all()


class ModelRequestGate:
    def __init__(self, *, background_after=None, foreground_burst=4):
        if (background_after is not None and not 0 < background_after <= 20) or not 1 <= foreground_burst <= 32:
            raise ValueError('Unbounded model scheduling policy')
        self.background_after, self.foreground_burst = background_after, foreground_burst
        self.condition = threading.Condition()
        self.active = 0
        self.background_active = 0
        self.foreground_grants = 0
        self.foreground = deque()
        self.background = deque()

    def snapshot(self):
        with self.condition:
            return {'active': self.active, 'waiting_foreground': len(self.foreground),
                'waiting_background': len(self.background)}

    def acquire(self, *, foreground, cancelled=lambda: False, timeout=30):
        deadline = time.monotonic() + timeout
        ticket = (object(), time.monotonic())
        queue = self.foreground if foreground else self.background
        with self.condition:
            if len(self.foreground) + len(self.background) >= 128:
                raise ModelQueueError('model_request_queue_full')
            if not foreground and not queue:
                self.foreground_grants = 0
            queue.append(ticket)
            try:
                while True:
                    if cancelled():
                        raise ModelQueueError('model_request_cancelled')
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ModelQueueError('model_request_queue_timeout')
                    due = (self.background_after is not None and self.background and self.background_active == 0
                        and time.monotonic() - self.background[0][1] >= self.background_after
                        and self.foreground_grants >= self.foreground_burst)
                    preferred = self.background if due or not self.foreground else self.foreground
                    if preferred is self.background and self.background_after is not None and self.background_active:
                        preferred = None
                    if self.active < 2 and preferred is queue and queue[0] is ticket:
                        queue.popleft()
                        self.active += 1
                        if foreground and self.background:
                            self.foreground_grants = min(self.foreground_burst, self.foreground_grants + 1)
                        elif not foreground:
                            self.background_active += 1
                            self.foreground_grants = 0
                        self.condition.notify_all()
                        return Lease(self, foreground)
                    self.condition.wait(min(.05, remaining))
            finally:
                if ticket in queue:
                    queue.remove(ticket)
                    self.condition.notify_all()


model_requests = ModelRequestGate(background_after=10, foreground_burst=4)
