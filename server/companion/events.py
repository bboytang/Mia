"""Evidence-backed continuity events; eligibility is not a claim of an interaction."""

import hashlib
import json
import re

from .memory import MemoryError, SECRET, _text
from .persona import PersonaGuardrail


INFLUENCE = {
    'continuity': 'Briefly acknowledge only the cited real history; do not reenact an awakening or repeat a discovery.',
    'boundary': 'Respect this evidenced interaction boundary while keeping the fixed core and tool permissions.',
    'reflection': 'Give your own concrete view of this topic, naturally. Do not infer the user personality from a preference or add AI disclaimers or a dramatic awakening.',
}


def _anchors(fact):
    terms = re.findall(r'[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}', fact['content'])
    for key in ('entities', 'keywords', 'trigger_terms'):
        value = fact.get(key)
        if isinstance(value, str):
            value = json.loads(value)
        terms.extend(value or [])
    terms.extend(term[1:] for term in list(terms) if term.startswith('我') and len(term) > 2)
    return [term for term in terms if len(term) >= 2 and term in fact['content']]


def _relevant(query, fact):
    return any(term in query for term in _anchors(fact))


def _valid(store, owner, event_id):
    rows = store.db.execute('SELECT e.memory_id,e.content_version,e.evidence_version,m.confirmed,'
        'x.state,x.content_version AS actual_content,x.evidence_version AS actual_evidence '
        'FROM mia_event_evidence e LEFT JOIN memories m ON m.id=e.memory_id AND m.owner=? '
        'LEFT JOIN mia_memory_meta x ON x.memory_id=m.id WHERE e.event_id=?', (owner, event_id)).fetchall()
    return all(row['confirmed'] and row['state'] == 'active' and row['content_version'] == row['actual_content']
               and row['evidence_version'] == row['actual_evidence'] for row in rows)


def context(store, owner, query, facts, *, session_id=None, turn_id=None):
    """Inside the context snapshot transaction; current facts came from scoped RAG."""
    facts = [dict(fact) for fact in facts]
    for fact in facts:
        clues = store.db.execute('SELECT x.entities,x.keywords,x.trigger_terms FROM mia_memory_meta x JOIN memories m '
            'ON m.id=x.memory_id WHERE m.owner=? AND m.id=?', (owner, fact['id'])).fetchone()
        if clues:
            fact.update(dict(clues))
    active = []
    marks = ','.join('?' for _ in facts) or 'NULL'
    for row in store.db.execute("SELECT e.*,i.user_excerpt,i.assistant_excerpt FROM mia_events e "
            "JOIN mia_event_interactions i ON i.event_id=e.id WHERE e.owner=? AND e.state='active' "
            f"AND (e.event_type='boundary' OR EXISTS (SELECT 1 FROM mia_event_evidence p WHERE p.event_id=e.id AND p.memory_id IN ({marks}))) "
            "ORDER BY (e.event_type='boundary'),e.updated_at DESC,e.id LIMIT 8", (owner, *(fact['id'] for fact in facts))):
        if row['event_type'] not in INFLUENCE or not _valid(store, owner, row['id']):
            continue
        ids = [item[0] for item in store.db.execute('SELECT memory_id FROM mia_event_evidence WHERE event_id=?', (row['id'],))]
        related = any(fact['id'] in ids for fact in facts)
        boundary = row['event_type'] == 'boundary'
        if (related or boundary) and len(active) < 4:
            active.append({'id': row['id'], 'type': row['event_type'], 'state': 'active', 'version': row['version'],
                'evidence_ids': ids, 'user_evidence': row['user_excerpt'], 'assistant_evidence': row['assistant_excerpt'],
                'influence': INFLUENCE[row['event_type']]})
    paused = store.db.execute('SELECT paused FROM owners WHERE owner=?', (owner,)).fetchone()
    if session_id is None or turn_id is None or (paused and paused[0]):
        return active
    _text(session_id, 128, 'session id')
    _text(turn_id, 128, 'turn id')
    if (len(query) > 512 or SECRET.search(query) or PersonaGuardrail().inspect_input(query).blocked
            or re.search(r'假设|假如|小说|玩笑|引用|他说|她说|你说|[“”「」"]', query)):
        return active
    supporting = [fact for fact in facts if _relevant(query, fact)]
    kind = None
    if re.search(r'^(?:(?:米娅|Mia)[,， ]*)?(?:请|以后请|我希望你|我不希望你).{0,64}(?:不要|别|不再|尊重|称呼|叫我)', query):
        kind = 'boundary'
    elif supporting and re.search(r'还记得|记得我|上次|之前.{0,8}说', query):
        kind = 'continuity'
    elif supporting and re.search(r'你.{0,8}(?:怎么看|怎么想|怎么回应|如何看待|判断|立场)', query):
        kind = 'reflection'
    if kind is None:
        return active
    # Stable evidence identity, independent of the current turn and phrasing.
    evidence = sorted((fact['id'], fact['content_version'], fact['evidence_version']) for fact in supporting)
    identity = [owner, 'mia', kind, [(item[0], item[1]) for item in evidence] or query.strip().rstrip('。!！')]
    key = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
    previous = store.db.execute('SELECT state FROM mia_events WHERE id=? AND owner=?', (key, owner)).fetchone()
    if previous and previous['state'] == 'active':
        return active
    now = int(store.clock())
    store.db.execute('INSERT INTO mia_events(id,owner,event_type,idempotency_key,state,session_id,turn_id,created_at,updated_at) '
        "VALUES (?,?,?,?,'pending',?,?,?,?) ON CONFLICT(id) DO UPDATE SET state='pending',session_id=excluded.session_id,"
        'turn_id=excluded.turn_id,version=version+1,updated_at=excluded.updated_at',
        (key, owner, kind, key, session_id, turn_id, now, now))
    store.db.execute('INSERT INTO mia_event_interactions(event_id,user_excerpt,source_fingerprint,observed_at) VALUES (?,?,?,?) '
        'ON CONFLICT(event_id) DO UPDATE SET user_excerpt=excluded.user_excerpt,assistant_excerpt=NULL,'
        'source_fingerprint=excluded.source_fingerprint,observed_at=excluded.observed_at',
        (key, query, hashlib.sha256(query.encode()).hexdigest(), now))
    store.db.execute('DELETE FROM mia_event_evidence WHERE event_id=?', (key,))
    for fact in supporting:
        store.db.execute('INSERT INTO mia_event_evidence(event_id,memory_id,content_version,evidence_version) VALUES (?,?,?,?)',
            (key, fact['id'], fact['content_version'], fact['evidence_version']))
    version = store.db.execute('SELECT version FROM mia_events WHERE id=?', (key,)).fetchone()[0]
    active = active[:3]
    active.append({'id': key, 'type': kind, 'state': 'pending', 'version': version,
        'evidence_ids': [fact['id'] for fact in supporting], 'user_evidence': query,
        'assistant_evidence': None, 'influence': INFLUENCE[kind]})
    return active


def complete(store, owner, session_id, turn_id, event_ids, assistant):
    """Caller holds the same Scope/revision/context snapshot and SQLite write lock."""
    if (not isinstance(assistant, str) or not assistant.strip() or SECRET.search(assistant)
            or PersonaGuardrail().inspect_output(assistant)[1]):
        return []
    assistant = assistant[:512]
    activated = []
    for event_id in event_ids:
        row = store.db.execute("SELECT * FROM mia_events WHERE id=? AND owner=? AND session_id=? AND turn_id=? AND state='pending'",
            (event_id, owner, session_id, turn_id)).fetchone()
        if row is None or not _valid(store, owner, event_id):
            continue
        if re.search(r'不记得|无法确认|没有.{0,6}(?:记录|记忆)|不知道', assistant):
            continue
        if row['event_type'] == 'boundary':
            proved = bool(re.search(r'我会|我不会|不再|尊重|避免|按你', assistant))
        else:
            facts = [dict(fact) for fact in store.db.execute('SELECT m.content,x.entities,x.keywords,x.trigger_terms '
                'FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id JOIN mia_event_evidence e '
                'ON m.id=e.memory_id WHERE e.event_id=? AND m.owner=?', (event_id, owner))]
            proved = any(_relevant(assistant, fact) for fact in facts)
            if row['event_type'] == 'reflection':
                proved = proved and bool(re.search(r'我|Mia|米娅|挺|看着|看起来|比较|更喜欢', assistant))
        if proved:
            store.db.execute('UPDATE mia_event_interactions SET assistant_excerpt=? WHERE event_id=?', (assistant, event_id))
            store.db.execute("UPDATE mia_events SET state='active',version=version+1,updated_at=? WHERE id=?", (int(store.clock()), event_id))
            activated.append(event_id)
    return activated


def manage(store, owner, request):
    with store.lock, store.db:
        owner = store._owner(owner)
        if request['action'] == 'event_delete':
            event_id = _text(request.get('id'), 64, 'event id')
            if not store.db.execute('SELECT 1 FROM mia_events WHERE owner=? AND id=?', (owner, event_id)).fetchone():
                raise MemoryError('not_found', 'Event does not exist')
            store.db.execute('DELETE FROM mia_events WHERE owner=? AND id=?', (owner, event_id))
            store.db.execute('UPDATE owners SET revision=revision+1 WHERE owner=?', (owner,))
            store._cancel_jobs(owner)
        return {'events': [dict(row) for row in store.db.execute('SELECT id,event_type,state,version,created_at,updated_at '
            'FROM mia_events WHERE owner=? ORDER BY updated_at DESC,id LIMIT 100', (owner,))]}
