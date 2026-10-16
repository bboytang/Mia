"""Service-owned durable extraction jobs; SQLite is the queue authority."""

import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib
import json
import threading
import sqlite3

from .authorization import AuthenticatedScope, PrivateAuthorizationRequired
from .memory import MemoryError, _safe_text
from .extraction import context_for, validate_output
from .embedding import EmbeddingUnavailable
from .semantic import SemanticMemoryIndex


ACTIVE = ('pending', 'extracting', 'validated', 'retry_wait')


@dataclass(frozen=True)
class TurnCompleted:
    scope: AuthenticatedScope
    session_id: str
    turn_id: str
    message_id: str
    text: str
    revision: int
    priority: bool = False


class JobStore:
    def __init__(self, store, capacity=128, lifetime=120):
        self.store, self.capacity, self.lifetime = store, capacity, lifetime

    def submit(self, event):
        if not isinstance(event.scope, AuthenticatedScope) or event.scope.persona_id != 'mia':
            raise PrivateAuthorizationRequired()
        text = _safe_text(event.text, 512, 'source')
        for value in (event.session_id, event.turn_id, event.message_id):
            _safe_text(value, 128, 'source id')
        key = hashlib.sha256(json.dumps([event.scope.owner, event.session_id, event.message_id]).encode()).hexdigest()
        now = int(self.store.clock())
        with self.store.lock, self.store.db:
            db = self.store.db
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT id,state FROM mia_jobs WHERE owner=? AND idempotency_key=?',
                                  (event.scope.owner, key)).fetchone()
            if previous:
                return dict(previous, status='duplicate')
            self.store._owner(event.scope.owner)
            state = db.execute('SELECT revision,paused FROM owners WHERE owner=?', (event.scope.owner,)).fetchone()
            if state['paused'] or state['revision'] != event.revision:
                return {'status': 'cancelled', 'code': 'memory_changed'}
            count = db.execute("SELECT COUNT(*) FROM mia_jobs WHERE state IN ('pending','extracting','validated','retry_wait')").fetchone()[0]
            if count >= self.capacity:
                return {'status': 'queue_full', 'accepted': False}
            # Stable identifiers, one bounded real user excerpt, no credential or assistant text.
            from .emotions import consent
            tracking = consent(self.store, event.scope.owner)
            db.execute('INSERT INTO mia_jobs(id,owner,idempotency_key,scope_snapshot,memory_revision,session_id,turn_id,'
                'source_payload,state,created_at,updated_at,deadline) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (key, event.scope.owner, key, json.dumps(event.scope.snapshot(), sort_keys=True), event.revision,
                 event.session_id, event.turn_id, json.dumps({'message_id': event.message_id, 'text': text,
                 'priority': event.priority, 'emotion_consent_version': tracking['version'] if tracking['enabled'] else None},
                 ensure_ascii=False), 'pending', now, now, now + self.lifetime))
            return {'status': 'accepted', 'accepted': True, 'id': key, 'state': 'pending'}

    def recover(self):
        with self.store.lock, self.store.db:
            self.store.db.execute("UPDATE mia_jobs SET state=CASE WHEN validated_result IS NULL THEN 'pending' ELSE 'validated' END "
                                  "WHERE state='extracting'")

    def ready(self):
        now = int(self.store.clock())
        with self.store.lock, self.store.db:
            from .emotions import prune
            prune(self.store)
            self.store.db.execute("UPDATE mia_jobs SET state='failed',error_category='deadline_exceeded',source_payload='{}',"
                "validated_result=NULL,updated_at=? WHERE state IN ('pending','extracting','validated','retry_wait') AND deadline<=?", (now, now))
            return [dict(row) for row in self.store.db.execute(
                "SELECT * FROM mia_jobs WHERE state IN ('pending','extracting','validated','retry_wait') "
                "AND (next_attempt_at IS NULL OR next_attempt_at<=?) ORDER BY created_at,rowid LIMIT ?", (now, self.capacity))]

    def update(self, job, state, *, result=None, error=None, attempt=False):
        now = int(self.store.clock())
        terminal = state not in ACTIVE
        with self.store.lock, self.store.db:
            self.store.db.execute('UPDATE mia_jobs SET state=?,validated_result=?,error_category=?,updated_at=?,'
                'next_attempt_at=?,attempts=attempts+?,source_payload=CASE WHEN ? THEN \'{}\' ELSE source_payload END '
                "WHERE id=? AND state IN ('pending','extracting','validated','retry_wait')",
                (state, result, error, now, now + 1 if state == 'retry_wait' else None, int(attempt), terminal, job['id']))

    def current(self, job):
        with self.store.lock:
            row = self.store.db.execute('SELECT * FROM mia_jobs WHERE id=?', (job['id'],)).fetchone()
            return dict(row)

    def eligible(self, job):
        with self.store.lock:
            current = self.current(job)
            state = self.store.snapshot(job['owner'])
            return (current['state'] in ACTIVE and current['deadline'] > self.store.clock()
                    and not state['paused'] and state['revision'] == job['memory_revision'])

    def commit(self, job, result, vectors=None):
        # Fact write and terminal job state share the fact store's transaction.
        return self.store.apply_extraction(job['owner'], job['session_id'], job['memory_revision'],
            [json.loads(job['source_payload'])['text']], result, job['id'], job_id=job['id'], prepared_vectors=vectors)


class NativeLane:
    """One daemon lane: cancellation cannot launch a second hung native call."""
    def __init__(self):
        self.done = threading.Event()
        self.done.set()

    async def call(self, function, timeout):
        if not self.done.is_set():
            raise RuntimeError('native_lane_busy')
        self.done.clear()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        def deliver(value, error):
            if not future.done():
                if error is None:
                    future.set_result(value)
                else:
                    future.set_exception(error)
        def run():
            try:
                value, error = function(), None
            except Exception as failure:
                value, error = None, failure
            finally:
                self.done.set()
            try:
                loop.call_soon_threadsafe(deliver, value, error)
            except RuntimeError:
                pass  # Process loop has closed; native work never writes to SQLite.
        threading.Thread(target=run, daemon=True, name='mia-memory-extractor').start()
        return await asyncio.wait_for(future, timeout)


class MemoryWorker:
    def __init__(self, jobs, authorization, resolve, *, extraction_timeout=30, encoder=None):
        self.jobs, self.authorization, self.resolve = jobs, authorization, resolve
        self.extraction_timeout = extraction_timeout
        self.index = SemanticMemoryIndex(jobs.store, encoder) if encoder is not None else None
        self.lane = NativeLane()
        self.queue = deque(maxlen=jobs.capacity)
        self.served, self.tick = {}, 0
        self.results = {}
        self.validation_feedback = {}
        self.foreground = 0
        self.closing = False
        self.task = None
        self.wake = asyncio.Event()

    async def start(self):
        await asyncio.to_thread(self.jobs.recover)
        self.task = asyncio.create_task(self.run(), name='mia-memory-worker')

    async def submit(self, event):
        if self.closing:
            return {'status': 'closing', 'accepted': False}
        await self.authorization.require(event.scope, 'memory:write')
        result = await asyncio.to_thread(self.jobs.submit, event)
        self.wake.set()
        return result

    async def _scope(self, job):
        scope = await self.authorization.restore(json.loads(job['scope_snapshot']))
        if scope.owner != job['owner'] or scope.persona_id != 'mia':
            raise PrivateAuthorizationRequired()
        await self.authorization.require(scope, 'memory:write')
        if job['deadline'] <= self.jobs.store.clock():
            await asyncio.to_thread(self.jobs.update, job, 'failed', error='deadline_exceeded')
        if not await asyncio.to_thread(self.jobs.eligible, job):
            raise PrivateAuthorizationRequired()
        return scope

    async def run_once(self):
        rows = await asyncio.to_thread(self.jobs.ready)
        active = {row['id'] for row in rows}
        self.results = {key: value for key, value in self.results.items() if key in active}
        self.validation_feedback = {key: value for key, value in self.validation_feedback.items() if key in active}
        if self.foreground or not self.lane.done.is_set():
            return False
        owners = {row['owner'] for row in rows}
        self.served = {owner: count for owner, count in self.served.items() if owner in owners}
        rows.sort(key=lambda row: (self.served.get(row['owner'], 0),
            not json.loads(row['source_payload']).get('priority', False), row['created_at']))
        self.queue.clear()
        self.queue.extend(rows)
        if not self.queue:
            return False
        job = self.queue.popleft()
        self.tick += 1
        self.served[job['owner']] = self.tick
        result = self.results.get(job['id'], job['validated_result'])
        try:
            scope = await self._scope(job)
            if result is None:
                if job['attempts'] >= 2:
                    await asyncio.to_thread(self.jobs.update, job, 'failed', error='attempts_exhausted')
                    return True
                context = await asyncio.to_thread(context_for, self.jobs.store, scope.owner,
                    json.loads(job['source_payload']).get('emotion_consent_version'))
                context.validation_feedback = self.validation_feedback.get(job['id'])
                extract = await self.resolve(scope)
                # A newly active front-end gets priority before entering a native call.
                if self.foreground:
                    return False
                await asyncio.to_thread(self.jobs.update, job, 'extracting', attempt=True)
                try:
                    output = await self.lane.call(lambda: extract([json.loads(job['source_payload'])['text']], context),
                        min(self.extraction_timeout, max(0.001, job['deadline'] - self.jobs.store.clock())))
                except asyncio.TimeoutError:
                    raise TimeoutError('extraction_timeout') from None
                try:
                    validated = validate_output(output, [json.loads(job['source_payload'])['text']], context)
                except MemoryError as error:
                    if error.code == 'invalid_input' and job['attempts'] + 1 < 2:
                        # Server validation messages only; never provider errors,
                        # raw model text, extra sources or output repair.
                        self.validation_feedback[job['id']] = str(error)[:512]
                    raise
                self.validation_feedback.pop(job['id'], None)
                result = json.dumps(validated, ensure_ascii=False)
                self.results[job['id']] = result
                await self._scope(job)
            if json.loads(result).get('_schema') != 1:
                raise MemoryError('extractor_version_changed', 'Unverified legacy task result')
            if result is not None:
                await asyncio.to_thread(self.jobs.update, job, 'validated', result=result)
                self.results.pop(job['id'], None)
            await self._scope(job)
            structured = json.loads(result)
            vectors = {}
            for i, record in enumerate(structured['memories']):
                if not record['sensitive'] and record['kind'] == 'explicit':
                    if self.index is None:
                        raise EmbeddingUnavailable('embedding_assets_unconfigured')
                    vector = await self.lane.call(lambda: self.index.encoder.encode(record['content']), 3)
                    vectors[i] = self.index._vector(vector).tobytes()
            await self._scope(job)
            await asyncio.to_thread(self.jobs.commit, job, structured, vectors)
        except PrivateAuthorizationRequired:
            await asyncio.to_thread(self.jobs.update, job, 'cancelled', error='authorization_or_memory_changed')
            self.results.pop(job['id'], None)
        except MemoryError as error:
            if error.code in {'evidence_changed', 'extractor_version_changed'}:
                await asyncio.to_thread(self.jobs.update, job, 'cancelled', error=error.code)
                self.results.pop(job['id'], None)
                return True
            current = await asyncio.to_thread(self.jobs.current, job)
            await asyncio.to_thread(self.jobs.update, job, 'failed' if current['attempts'] >= 2 else 'retry_wait',
                                    error='invalid_output')
        except Exception as error:
            current = await asyncio.to_thread(self.jobs.current, job)
            category = ('database' if isinstance(error, sqlite3.Error) else
                        'embedding' if isinstance(error, EmbeddingUnavailable) else
                        'timeout' if isinstance(error, TimeoutError) else 'model')
            terminal = result is None and current['attempts'] >= 2
            await asyncio.to_thread(self.jobs.update, job, 'failed' if terminal else 'retry_wait',
                                    result=result, error=category)
        return True

    async def run(self):
        while not self.closing:
            try:
                worked = await self.run_once()
            except Exception:
                # DB outage: durable rows remain authoritative; retry without a spin.
                worked = False
            if not worked:
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), 0.25)
                except asyncio.TimeoutError:
                    pass

    async def close(self, timeout=20):
        self.closing = True
        self.wake.set()
        if self.task:
            done, pending = await asyncio.wait({self.task}, timeout=timeout)
            for task in pending:
                task.cancel()
            # No wait for an uncooperative model thread or a fresh per-job deadline.
            return not pending
        return True
