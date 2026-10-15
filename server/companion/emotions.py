"""Opt-in observations and derived rolling trends; no model or second fact store."""

from collections import Counter
import hashlib
import json
import re

from .memory import MemoryError, SECRET, _text


DAY = 86400
TENDENCIES = {'positive', 'negative', 'neutral', 'mixed'}
KINDS = {'self_report', 'inferred'}
RELEVANT = re.compile(r'情绪|心情|状态|最近.{0,12}(?:感觉|怎么样)|这些天.{0,12}感觉|\bmood\b|\bfeeling\b', re.I)
AFFECT = re.compile(r'开心|快乐|高兴|轻松|安心|满足|平静|难过|伤心|焦虑|紧张|低落|烦躁|疲惫|沮丧|担心|压力|孤独|害怕|生气|愤怒|心情|情绪')
VALENCE = {'positive': re.compile(r'开心|快乐|高兴|轻松|安心|满足'),
           'negative': re.compile(r'难过|伤心|焦虑|紧张|低落|烦躁|疲惫|沮丧|担心|压力|孤独|害怕|生气|愤怒'),
           'neutral': re.compile(r'平静|平稳|平常|一般|没什么情绪')}


def explicit_tendencies(quote):
    found = set()
    for label, pattern in VALENCE.items():
        for match in pattern.finditer(quote):
            negated = bool(re.search(r'不|没|并非|不是', quote[max(0, match.start() - 3):match.start()]))
            found.add(('negative' if label == 'positive' else 'neutral') if negated else label)
    return {'mixed'} if len(found) > 1 else found


def consent(store, owner):
    row = store.db.execute('SELECT enabled,version,enabled_at,disabled_at FROM mia_emotion_consent WHERE owner=?', (owner,)).fetchone()
    return dict(row) if row else {'enabled': 0, 'version': 0, 'enabled_at': None, 'disabled_at': None}


def validate_observations(raw, sources, tracking):
    from .extraction import normalize, source_supported
    if not isinstance(raw, list) or len(raw) > 1:
        raise MemoryError('invalid_input', 'At most one observation per user message')
    if raw and not tracking['enabled']:
        raise MemoryError('invalid_input', 'Emotion tracking is disabled')
    result = []
    for item in raw:
        if not isinstance(item, dict):
            raise MemoryError('invalid_input', 'Invalid observation')
        index, kind, tendency, confidence = (item.get(k) for k in ('source_index', 'source_kind', 'tendency', 'confidence'))
        quote = item.get('source_quote')
        if (type(index) is not int or not 0 <= index < len(sources) or not isinstance(kind, str) or kind not in KINDS
                or not isinstance(tendency, str) or tendency not in TENDENCIES
                or type(confidence) not in (int, float) or not 0.5 <= confidence <= 1
                or item.get('subject') != 'user' or not isinstance(quote, str) or not 1 <= len(quote) <= 512):
            raise MemoryError('invalid_input', 'Invalid observation classification')
        quote = normalize(quote)
        if (quote not in normalize(sources[index]) or not source_supported(sources[index], quote, allow_transient=True)
                or not re.match(r'^(?:(?:最近|今天|现在|这些天|这几天|这周|这阵子)[,， ]*)?我', quote)
                or SECRET.search(quote)):
            raise MemoryError('invalid_input', 'Observation lacks real first-person evidence')
        if kind == 'self_report' and not AFFECT.search(quote):
            raise MemoryError('invalid_input', 'Self-report has no explicit affect evidence')
        explicit = explicit_tendencies(quote)
        if kind == 'self_report' and tendency not in explicit:
            raise MemoryError('invalid_input', 'Self-report tendency contradicts its evidence')
        if kind == 'inferred' and confidence > 0.6:
            raise MemoryError('invalid_input', 'Inferred emotion confidence is capped')
        result.append({'source_index': index, 'source_quote': quote, 'source_kind': kind,
                       'subject': 'user', 'tendency': tendency, 'confidence': confidence})
    return result


def commit(store, job, structured):
    """Called inside the authoritative fact/job transaction, after Scope checks."""
    payload = json.loads(job['source_payload'])
    current = consent(store, job['owner'])
    expected = payload.get('emotion_consent_version')
    if not current['enabled'] or expected != current['version'] or structured.get('emotion_consent_version') != expected:
        return 0
    count = 0
    for item in structured.get('observations', []):
        key = hashlib.sha256(json.dumps([job['owner'], job['session_id'], payload['message_id'], item['source_kind']]).encode()).hexdigest()
        store.db.execute('INSERT OR IGNORE INTO mia_observations(id,owner,subject,source_kind,session_id,turn_id,message_id,'
            'observed_at,created_at,consent_version,tendency,confidence,source_excerpt,state) '
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'active')", (key, job['owner'], 'user', item['source_kind'],
            job['session_id'], job['turn_id'], payload['message_id'], job['created_at'], int(store.clock()),
            expected, item['tendency'], item['confidence'], item['source_quote']))
        store.db.execute('INSERT OR IGNORE INTO mia_observation_meta(observation_id,source_fingerprint) VALUES (?,?)',
            (key, hashlib.sha256(payload['text'].encode()).hexdigest()))
        count += 1
    return count


def prune(store):
    # Calendar windows use UTC server dates, never dates supplied by the model/client.
    start = (int(store.clock()) // DAY - 89) * DAY
    store.db.execute('DELETE FROM mia_observations WHERE observed_at<?', (start,))


def trend(store, owner, *, for_reply=True):
    setting = consent(store, owner)
    if not setting['enabled'] and for_reply:
        return {'status': 'disabled'}
    now = int(store.clock())
    start = (now // DAY - 29) * DAY
    recent = (now // DAY - 6) * DAY
    rows = [dict(row) for row in store.db.execute("SELECT o.id,o.session_id,o.observed_at,o.source_kind,o.tendency,o.confidence "
        "FROM mia_observations o JOIN mia_observation_meta x ON x.observation_id=o.id "
        "WHERE o.owner=? AND o.subject='user' AND o.state='active' AND o.observed_at>=? AND o.observed_at<=? "
        'ORDER BY o.observed_at,o.id', (owner, start, now))]
    groups = {}
    for kind in sorted(KINDS):
        selected = [row for row in rows if row['source_kind'] == kind]
        sessions = len({row['session_id'] for row in selected})
        span = (selected[-1]['observed_at'] // DAY - selected[0]['observed_at'] // DAY + 1) if selected else 0
        ready = len(selected) >= 5 and sessions >= 3 and span >= 7
        groups[kind] = {'status': 'available' if ready else 'insufficient_observations', 'count': len(selected),
            'sessions': sessions, 'calendar_span_days': span,
            'distribution': dict(Counter(row['tendency'] for row in selected)) if ready else {},
            'recent_7_days': dict(Counter(row['tendency'] for row in selected if row['observed_at'] >= recent)) if ready else {},
            'previous_days': dict(Counter(row['tendency'] for row in selected if row['observed_at'] < recent)) if ready else {},
            'mean_confidence': sum(row['confidence'] for row in selected) / len(selected) if ready else None,
            'evidence_ids': [row['id'] for row in selected[-8:]] if ready else []}
    return {'status': ('available' if any(g['status'] == 'available' for g in groups.values()) else 'insufficient_observations'),
        'enabled': bool(setting['enabled']), 'consent_version': setting['version'], 'window_days': 30,
        'timezone': 'UTC', 'groups': groups, 'interpretation': 'Source-labelled observations, not a diagnosis or measured inner feelings.'}


def manage(store, owner, request):
    action = request['action']
    with store.lock, store.db:
        store.db.execute('BEGIN IMMEDIATE')
        owner = store._owner(owner)
        prune(store)
        if action == 'emotion_consent':
            enabled = request.get('enabled')
            if type(enabled) is not bool:
                raise MemoryError('invalid_input', 'Invalid emotion consent')
            now = int(store.clock())
            store.db.execute('INSERT INTO mia_emotion_consent(owner,enabled,version,enabled_at,disabled_at) VALUES (?,?,1,?,?) '
                'ON CONFLICT(owner) DO UPDATE SET enabled=excluded.enabled,version=version+1,'
                'enabled_at=CASE WHEN excluded.enabled THEN excluded.enabled_at ELSE enabled_at END,'
                'disabled_at=CASE WHEN excluded.enabled THEN disabled_at ELSE excluded.disabled_at END',
                (owner, enabled, now if enabled else None, None if enabled else now))
        elif action in {'observation_update', 'observation_delete'}:
            observation_id = _text(request.get('id'), 64, 'observation id')
            row = store.db.execute('SELECT id FROM mia_observations WHERE owner=? AND id=?', (owner, observation_id)).fetchone()
            if row is None:
                raise MemoryError('not_found', 'Observation does not exist')
            if action == 'observation_delete':
                store.db.execute('DELETE FROM mia_observations WHERE id=?', (observation_id,))
            else:
                tendency = request.get('tendency')
                if not isinstance(tendency, str) or tendency not in TENDENCIES:
                    raise MemoryError('invalid_input', 'Invalid corrected tendency')
                store.db.execute("UPDATE mia_observations SET tendency=?,source_kind='self_report',confidence=1,state='active' WHERE id=?", (tendency, observation_id))
                store.db.execute("UPDATE mia_observation_meta SET version=version+1,correction_origin='user_management' WHERE observation_id=?", (observation_id,))
        elif action == 'emotion_clear':
            store.db.execute('DELETE FROM mia_observations WHERE owner=?', (owner,))
        elif action not in {'emotion_status', 'observations'}:
            raise MemoryError('invalid_input', 'Unknown emotion action')
        if action not in {'emotion_status', 'observations'}:
            store.db.execute('UPDATE owners SET revision=revision+1 WHERE owner=?', (owner,))
            store._cancel_jobs(owner)
        result = {'consent': consent(store, owner), 'trend': trend(store, owner, for_reply=False)}
        if action == 'observations':
            result['observations'] = [dict(row) for row in store.db.execute('SELECT o.*,x.version,x.correction_origin '
                'FROM mia_observations o LEFT JOIN mia_observation_meta x ON x.observation_id=o.id '
                'WHERE o.owner=? ORDER BY o.observed_at DESC,o.id LIMIT 100', (owner,))]
    if action in {'observation_delete', 'emotion_clear'}:
        with store.lock:
            store._purge()
    return result
