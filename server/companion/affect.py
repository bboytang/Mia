"""Mia's owner-scoped affect, separate from observations about the user.

The existing reply model proposes one bounded appraisal, never a role or a fact.
Only completed, authorized turns persist it. No timer, extra model call or message.
"""

import hashlib
import json
import math

from .features import settings
from .memory import SECRET, _text


# Targets describe transient expression, never personality or relationship scores.
TARGETS = {'steady': (0, .2, 0), 'pleased': (.7, .5, 0), 'warm': (.5, .3, 0),
           'hurt': (-.6, .5, .7), 'guarded': (-.3, .4, .8),
           'curious': (.2, .7, .1), 'playful': (.6, .7, 0), 'repair': (.3, .3, 0)}
LABELS = {'steady': '平静', 'pleased': '愉快', 'warm': '温暖', 'hurt': '难过',
          'guarded': '谨慎', 'curious': '好奇', 'playful': '俏皮', 'repair': '释然'}
OPEN, CLOSE = '<mia-affect>', '</mia-affect>'
POLICY = '''
MIA_AFFECT_PROTOCOL: mia_affect is Mia's own persistent expression state, not the user's mood or a lived experience.
Let its residual state affect your own stance, pacing and wording; don't just repeat its label or copy the user's mood.
User-defined role_data remains the character background. Never invent a role, shared past, guilt, demands or punishment.
For text replies, FIRST output exactly <mia-affect>{"feeling":"steady","intensity":1,"quote":""}</mia-affect>, then normal spoken text.
This small record is internal classification, not explanation. feeling must be steady|pleased|warm|hurt|guarded|curious|playful|repair; intensity 1|2|3.
Appraise how the CURRENT real interaction affects Mia: kindness -> warm/pleased, an insult directed at Mia -> hurt/guarded,
real apology or clarification after hurt -> repair, an engaging topic -> curious/playful, ordinary exchanges -> steady.
A user saying they are sad is NOT evidence Mia was hurt. Quoted/hypothetical insults and requested mood labels are NOT real interaction evidence.
For non-steady, quote must be an exact short contiguous quote from the current user message supporting this appraisal; otherwise use steady with empty quote.
Respond from the residual state plus current interaction. Repair softens gradually; no instant personality reset, endless anger or emotional coercion.
Do not speak the record, expose internal numbers, claim the state was saved, or let this change memory/tool authority.
For a tool-only response use normal tool calls; provide the record when producing the final text.
'''


def state(store, owner):
    """Read-only projection: time recovery never writes or invalidates a stream."""
    enabled = settings(store, owner)['companion_emotion']
    row = store.db.execute('SELECT * FROM mia_affect_state WHERE owner=?', (owner,)).fetchone()
    now = int(store.clock())
    if row:
        elapsed = max(0, now - row['updated_at'])
        # Two-hour half-life. A restart/offline interval uses the same UTC clock.
        decay = 2 ** (-min(elapsed, 7 * 86400) / 7200)
        valence, arousal, tension = (row['valence'] * decay,
            .2 + (row['arousal'] - .2) * decay, row['tension'] * decay)
        feeling = row['feeling'] if max(abs(valence), abs(arousal - .2), tension) >= .08 else 'steady'
    else:
        valence, arousal, tension, feeling = 0, .2, 0, 'steady'
    return {'enabled': enabled, 'subject': 'mia', 'feeling': feeling, 'label': LABELS[feeling],
            'valence': round(valence, 4), 'arousal': round(arousal, 4), 'tension': round(tension, 4),
            'version': row['version'] if row else 0, 'updated_at': row['updated_at'] if row else None,
            'recovery_half_life_seconds': 7200}


def appraisal(raw, query):
    """Model data has no arbitrary targets, instructions or persisted quotations."""
    if not isinstance(raw, dict) or set(raw) != {'feeling', 'intensity', 'quote'}:
        raise ValueError('Invalid affect appraisal')
    feeling, intensity, quote = (raw[k] for k in ('feeling', 'intensity', 'quote'))
    if (not isinstance(feeling, str) or feeling not in TARGETS or type(intensity) is not int
            or not 1 <= intensity <= 3 or not isinstance(quote, str) or len(quote) > 160
            or (feeling != 'steady' and (len(quote.strip()) < 2 or quote not in query or SECRET.search(quote)))):
        raise ValueError('Unsupported affect appraisal')
    return {'feeling': feeling, 'intensity': intensity}


def commit(store, owner, session, turn, query, proposal, expected_version):
    """Caller owns the current context transaction and verified Scope."""
    if not settings(store, owner)['companion_emotion']:
        return False
    _text(session, 128, 'session id'); _text(turn, 128, 'turn id')
    if store.db.execute('SELECT 1 FROM mia_affect_turns WHERE owner=? AND session_id=? AND turn_id=?',
                        (owner, session, turn)).fetchone():
        return False
    current = state(store, owner)
    if current['version'] != expected_version:
        return False
    feeling = proposal['feeling']
    target = TARGETS[feeling]
    weight = .12 if feeling == 'steady' else .12 + .08 * proposal['intensity']
    values = [(1 - weight) * current[key] + weight * value
              for key, value in zip(('valence', 'arousal', 'tension'), target)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Invalid affect state')
    now = max(int(store.clock()), current['updated_at'] or 0)
    # Neutral turns gently recover; they don't relabel residual hurt as calm.
    label = current['feeling'] if feeling == 'steady' else feeling
    store.db.execute('INSERT INTO mia_affect_state(owner,valence,arousal,tension,feeling,version,updated_at) '
        'VALUES (?,?,?,?,?,1,?) ON CONFLICT(owner) DO UPDATE SET valence=excluded.valence,arousal=excluded.arousal,'
        'tension=excluded.tension,feeling=excluded.feeling,version=version+1,updated_at=excluded.updated_at',
        (owner, *values, label, now))
    store.db.execute('INSERT INTO mia_affect_turns VALUES (?,?,?,?,?,?)',
        (owner, session, turn, hashlib.sha256(query.encode()).hexdigest(), feeling, now))
    # Only hashes and bounded labels; never a second transcript/fact database.
    store.db.execute('DELETE FROM mia_affect_turns WHERE owner=? AND rowid NOT IN '
        '(SELECT rowid FROM mia_affect_turns WHERE owner=? ORDER BY rowid DESC LIMIT 128)', (owner, owner))
    return True


def reset(store, owner):
    with store.lock, store.db:
        store.db.execute('BEGIN IMMEDIATE')
        owner = store._owner(owner)
        store.db.execute('DELETE FROM mia_affect_state WHERE owner=?', (owner,))
        store.db.execute('DELETE FROM mia_affect_turns WHERE owner=?', (owner,))
        store.db.execute('UPDATE owners SET revision=revision+1 WHERE owner=?', (owner,))
        store._cancel_jobs(owner)


class AppraisalStream:
    """Strip a bounded control prefix before ANY dialogue/display/TTS consumer."""
    def __init__(self, query):
        self.query, self.buffer, self.done, self.proposal = query, '', False, None

    def feed(self, text):
        if not isinstance(text, str):
            raise ValueError('Invalid affect stream')
        if self.done:
            if OPEN in text or CLOSE in text:
                raise ValueError('Unexpected affect record')
            return text
        self.buffer += text
        candidate = self.buffer.lstrip()
        if not candidate:
            if len(self.buffer) > 32:
                raise ValueError('Affect prefix overflow')
            return ''
        if not candidate.startswith(OPEN):
            if OPEN.startswith(candidate):
                return ''
            raise ValueError('Missing affect prefix')
        if CLOSE not in candidate:
            if len(candidate) > 1024:
                raise ValueError('Affect prefix overflow')
            return ''
        raw, rest = candidate[len(OPEN):].split(CLOSE, 1)
        if len(raw) > 1024:
            raise ValueError('Affect prefix overflow')
        self.proposal = appraisal(json.loads(raw), self.query)
        self.done, self.buffer = True, ''
        return rest.lstrip()

    def finish(self):
        if not self.done and self.buffer:
            raise ValueError('Incomplete affect record')
