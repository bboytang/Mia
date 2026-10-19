import asyncio
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from youmi_query_scheduling import serialize_query_encodes


class SyntheticIndex:
    def __init__(self):
        self.active = set()
        self.peak = 0
        self.release = asyncio.Event()
        self.two_requests_entered = asyncio.Event()
        self.calls = []

    async def _encode(self, request, number):
        if request in self.active:
            raise AssertionError('Encodes from one request overlapped')
        self.active.add(request)
        self.peak = max(self.peak, len(self.active))
        self.calls.append((request, number))
        if len(self.active) == 2:
            self.two_requests_entered.set()
        try:
            await self.release.wait()
            return request, number
        finally:
            self.active.remove(request)

    async def retrieve(self, request):
        return await asyncio.gather(self._encode(request, 0), self._encode(request, 1))


class QuerySchedulingTests(unittest.IsolatedAsyncioTestCase):
    async def test_serial_pairs_keep_two_requests_concurrent_and_preserve_values(self):
        index = SyntheticIndex()
        serialize_query_encodes(index)
        tasks = [asyncio.create_task(index.retrieve(request)) for request in ('first', 'second')]
        try:
            await asyncio.wait_for(index.two_requests_entered.wait(), 1)
            self.assertEqual(set(index.calls), {('first', 0), ('second', 0)})
            self.assertEqual(index.peak, 2)
        finally:
            index.release.set()
            results = await asyncio.gather(*tasks)
        self.assertEqual(results, [[('first', 0), ('first', 1)], [('second', 0), ('second', 1)]])
        self.assertEqual(index.active, set())

    async def test_cancellation_resets_request_context_and_does_not_hold_background(self):
        index = SyntheticIndex()
        serialize_query_encodes(index)
        task = asyncio.create_task(index.retrieve('cancelled'))
        background = asyncio.create_task(index._encode('background', 0))
        try:
            await asyncio.wait_for(index.two_requests_entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(index.active, {'background'})
        finally:
            index.release.set()
            await asyncio.gather(task, background, return_exceptions=True)
        self.assertEqual(await index.retrieve('next'), [('next', 0), ('next', 1)])
        self.assertEqual(index.active, set())


if __name__ == '__main__':
    unittest.main()
