"""Healthy-path per-request serialization trial; never production or acceptance."""

import asyncio
from contextvars import ContextVar
from functools import wraps


def serialize_query_encodes(index):
    """Keep different requests concurrent, serialize only each request's pair.

    This is a scheduling diagnostic, not the historical serial implementation:
    gather's error draining remains current. Fault behavior is not compared.
    Native inference, slots, scoring, authorization and background calls remain
    original. Child encode tasks inherit their own request's context.
    """
    request_lock = ContextVar('mia_trial_request_lock', default=None)
    retrieve, encode = index.retrieve, index._encode

    @wraps(retrieve)
    async def serial_retrieve(*args, **kwargs):
        token = request_lock.set(asyncio.Lock())
        try:
            return await retrieve(*args, **kwargs)
        finally:
            request_lock.reset(token)

    @wraps(encode)
    async def serial_encode(*args, **kwargs):
        lock = request_lock.get()
        if lock is None:
            return await encode(*args, **kwargs)
        async with lock:
            return await encode(*args, **kwargs)

    index.retrieve, index._encode = serial_retrieve, serial_encode
