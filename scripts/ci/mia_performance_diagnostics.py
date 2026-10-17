"""Observe the original index methods; profiling samples do not score D08."""

import cProfile
from contextlib import contextmanager
import functools
from pathlib import Path
import pstats
import threading
import time


class Timings:
    def __init__(self):
        self.values = {}
        self.local = threading.local()
        self.lock = threading.Lock()

    def add(self, name, elapsed):
        with self.lock:
            self.values.setdefault(name, []).append(elapsed * 1000)

    @contextmanager
    def stage(self, name):
        previous = getattr(self.local, 'stage', 'other')
        self.local.stage = name
        try:
            yield
        finally:
            self.local.stage = previous


class ObservedLock:
    def __init__(self, original, timings, name):
        self.original, self.timings, self.name = original, timings, name

    def __enter__(self):
        started = time.perf_counter()
        self.original.acquire()
        self.timings.add(self.name + '.' + getattr(self.timings.local, 'stage', 'other'),
                         time.perf_counter() - started)
        return self

    def __exit__(self, *args):
        self.original.release()


async def diagnose(index, current, auth, queries, summary, competing):
    """Single/competing original retrieves, then one separately marked profile."""
    timings = Timings()
    originals = {}
    profiles = []
    profiling = False

    def sync_observer(name, original):
        @functools.wraps(original)
        def measured(*args, **kwargs):
            with timings.stage(name):
                profiler = cProfile.Profile() if profiling and name == '_scan' else None
                started = time.perf_counter()
                if profiler:
                    profiler.enable()
                try:
                    return original(*args, **kwargs)
                finally:
                    if profiler:
                        profiler.disable()
                        profiles.append(profiler)
                    timings.add(name, time.perf_counter() - started)
        return measured

    def async_observer(name, original):
        @functools.wraps(original)
        async def measured(*args, **kwargs):
            started = time.perf_counter()
            try:
                return await original(*args, **kwargs)
            finally:
                timings.add(name, time.perf_counter() - started)
        return measured

    store_lock, encoder_lock, encode = index.store.lock, index.encoder._lock, index.encoder.encode
    try:
        index.store.lock = ObservedLock(store_lock, timings, 'store_lock_wait')
        index.encoder._lock = ObservedLock(encoder_lock, timings, 'encoder_lock_wait')
        index.encoder.encode = sync_observer('native_encode', encode)
        for name in ('_snapshot', '_clues', '_scan', '_snapshot_check'):
            originals[name] = getattr(index, name)
            setattr(index, name, sync_observer(name, originals[name]))
        for name in ('_encode', '_require'):
            originals[name] = getattr(index, name)
            setattr(index, name, async_observer(name, originals[name]))

        for query in queries:
            await index.retrieve(current, auth, query)
        timings.values.clear()
        pipeline = []
        for query in queries:
            for _ in range(5):
                started = time.perf_counter()
                await index.retrieve(current, auth, query)
                pipeline.append((time.perf_counter() - started) * 1000)
        sequential = {name: summary(values) for name, values in timings.values.items()}
        timings.values.clear()
        competition = await competing()
        concurrent = {name: summary(values) for name, values in timings.values.items()}

        # Profile an original retrieve after timed sampling; never mix its
        # substantial profiler overhead into performance thresholds.
        profiling = True
        await index.retrieve(current, auth, queries[0])
        stats = pstats.Stats(profiles[0]).stats
        functions = [{'file': Path(key[0]).name, 'line': key[1], 'function': key[2],
                      'primitive_calls': value[0], 'calls': value[1],
                      'self_ms': value[2] * 1000, 'cumulative_ms': value[3] * 1000}
                     for key, value in stats.items()]
        functions.sort(key=lambda item: item['cumulative_ms'], reverse=True)
        return {'scope': 'Instrumented original methods; no runtime or ranking modification; not D08 acceptance',
                'sequential_pipeline': summary(pipeline), 'sequential_stages': sequential,
                'competition': competition, 'concurrent_stages': concurrent,
                'separate_scan_profile': functions[:30]}
    finally:
        for name, original in originals.items():
            setattr(index, name, original)
        index.store.lock, index.encoder._lock, index.encoder.encode = store_lock, encoder_lock, encode
