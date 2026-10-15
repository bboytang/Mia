"""The existing connection's single provider path, with scoped turn snapshots."""

import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import threading

from .authorization import AuthenticatedScope, PrivateAuthorizationRequired, require_connection
from .context import ContextBuilder, ContextError, ContextLimits, packed
from .embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable, SemanticEncoder
from .semantic import SemanticMemoryIndex


class OfflineEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION

    def __init__(self):
        self.lock = threading.Lock()
        self.encoder = None

    def encode(self, text, query=False):
        with self.lock:
            if self.encoder is None:
                directory = os.environ.get('MIA_EMBEDDING_DIR')
                if not directory:
                    raise EmbeddingUnavailable('embedding_assets_unconfigured')
                self.encoder = SemanticEncoder(directory)
        return self.encoder.encode(text, query)


class UnavailableIndex:
    @property
    def store(self):
        raise sqlite3.OperationalError('Context database unavailable')

    async def _require(self, scope, authorization, permission):
        if not isinstance(scope, AuthenticatedScope) or scope.persona_id != 'mia':
            raise PrivateAuthorizationRequired()
        await authorization.require(scope, permission)

    async def retrieve(self, *args):
        raise EmbeddingUnavailable('context_database_unavailable')


_encoder = OfflineEncoder()
_builders = {}
_lock = threading.Lock()


def builder_for(store):
    if store is None:
        return ContextBuilder(UnavailableIndex())
    with _lock:
        if store not in _builders:
            _builders[store] = ContextBuilder(SemanticMemoryIndex(store, _encoder))
        return _builders[store]


def provider_limits(provider):
    # This file is a reviewed server artifact, never a hello/listen/client field.
    # Bind capacity to the exact provider, endpoint and model; no alias guessing.
    try:
        profile = json.loads(Path(os.environ['MIA_CONTEXT_PROFILE_FILE']).read_text(encoding='utf-8'))
        if (profile['provider_module'] != type(provider).__module__
                or profile['model'] != provider.model_name
                or profile['base_url'].rstrip('/') != provider.base_url.rstrip('/')):
            raise ValueError()
        return ContextLimits.from_provider(provider, profile['context_window'], profile['capacity_source'])
    except (OSError, KeyError, AttributeError, TypeError, ValueError):
        raise ContextError('context_limits_unverified') from None


def actual_messages(dialogue):
    # Deliberately bypass upstream's synthetic interrupted results and system
    # memory insertion. Display DTOs remain the existing authority, unchanged.
    result = []
    for message in list(dialogue.dialogue):
        if message.role == 'system' or getattr(message, 'is_temporary', False):
            continue
        value = {'role': message.role, 'content': message.content}
        if message.tool_calls is not None:
            value['tool_calls'] = message.tool_calls
        if message.tool_call_id is not None:
            value['tool_call_id'] = message.tool_call_id
        result.append((message.uniq_id, value))
    return result


@dataclass(frozen=True)
class ReplyTurn:
    builder: ContextBuilder
    bundle: object
    user_marker: str
    consumed_json: str


async def validate(conn, turn=None):
    await require_connection(conn)
    turn = turn or getattr(conn, '_mia_context_turn', None)
    if turn is None or turn.bundle.scope != getattr(conn, '_mia_scope', None):
        raise ContextError('context_turn_unavailable')
    limits = await asyncio.to_thread(provider_limits, conn.llm)
    if limits != turn.bundle.limits:
        raise ContextError('context_limits_changed')
    await turn.builder.validate(turn.bundle, conn._mia_authorization)
    return turn


async def prepare(conn, functions, depth):
    await require_connection(conn)
    limits = await asyncio.to_thread(provider_limits, conn.llm)
    builder = conn._mia_context_builder
    rows = actual_messages(conn.dialogue)
    turn = getattr(conn, '_mia_context_turn', None)
    tools = functions or []
    if depth == 0:
        if not rows or rows[-1][1]['role'] != 'user':
            raise ContextError('context_turn_unavailable')
        marker, current = rows[-1]
        query = current['content']
        history = [value for _, value in rows[:-1]]
        # History may contain old model-derived facts. Only keep it when the
        # last generation's full snapshot can still be proved current.
        previous = getattr(conn, '_mia_previous_context', None)
        if previous is None:
            history = []
        else:
            try:
                await validate(conn, previous)
            except ContextError:
                history = []
        bundle = await builder.build(conn._mia_scope, conn._mia_authorization, conn.sentence_id, query,
            limits=limits, history=history, role=getattr(conn, '_mia_role_data', ''), tools=tools, session_id=conn.session_id)
        consumed = [current]
    else:
        if turn is None:
            raise ContextError('context_turn_unavailable')
        marker, query = turn.user_marker, json.loads(turn.bundle.inputs_json)['query']
        try:
            await validate(conn, turn)
        except ContextError as error:
            if str(error) not in {'context_changed', 'context_snapshot_unavailable'}:
                raise
            # Re-query current facts, discard ALL old model/tool-derived data.
            # Already executed side effects are never replayed on a rebuild.
            bundle = await builder.build(conn._mia_scope, conn._mia_authorization, conn.sentence_id, query,
                limits=limits, role=getattr(conn, '_mia_role_data', ''), tools=[],
                scene='上下文已变化；旧工具结果已失效，本轮不再执行工具。需要新的工具操作时请用户重新发起。', session_id=conn.session_id)
            consumed = []
            marker = None
        else:
            start = next((i for i, (key, _) in enumerate(rows) if key == marker), None)
            if start is None:
                raise ContextError('context_turn_unavailable')
            current = [value for _, value in rows[start:]]
            consumed = json.loads(turn.consumed_json)
            if current[:len(consumed)] != consumed or not current[len(consumed):]:
                raise ContextError('context_turn_modified')
            bundle = await builder.continue_turn(turn.bundle, conn._mia_authorization,
                current[len(consumed):], tools=tools)
            consumed = current
    result = ReplyTurn(builder, bundle, marker, packed(consumed))
    await validate(conn, result)
    conn._mia_context_turn = result
    conn._mia_context_status = {'status': 'ready', 'turn_id': bundle.turn_id, **bundle.diagnostics()}
    return result


def wait(conn, operation):
    # chat() already runs in the existing executor; never call on the event loop.
    future = asyncio.run_coroutine_threadsafe(operation, conn.loop)
    try:
        return future.result(timeout=12)
    except FutureTimeout:
        future.cancel()
        raise ContextError('context_deadline_exceeded') from None


def response(conn, functions, depth):
    turn = wait(conn, prepare(conn, functions, depth))
    request = turn.bundle.request()
    tools = request.get('tools')
    # The same provider object/client/stream continues to own all generation.
    stream = (conn.llm.response_with_functions(conn.session_id, request['messages'], functions=tools,
                max_tokens=request['max_tokens']) if tools else
              conn.llm.response(conn.session_id, request['messages'], max_tokens=request['max_tokens']))
    def guarded():
        try:
            wait(conn, validate(conn, turn))
            for delta in stream:
                if getattr(conn, '_mia_context_turn', None) is not turn:
                    raise ContextError('context_turn_superseded')
                if getattr(conn, 'client_abort', False):
                    return
                wait(conn, validate(conn, turn))
                # Upstream parses pairs whenever its local functions is not None.
                yield delta if tools or functions is None else (delta, None)
            wait(conn, validate(conn, turn))
        finally:
            if hasattr(stream, 'close'):
                stream.close()
    return guarded()
