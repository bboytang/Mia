"""Mia's owner-scoped affect, separate from observations about the user.

The existing reply model proposes one bounded appraisal, never a role or a fact.
Only completed, authorized turns persist it. No timer, extra model call or message.
"""

import hashlib
import json
import math
import re

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
The record must precede every emoji or emotion label; put a suitable emoji only at the start of spoken text.
This small record is internal classification, not explanation. feeling must be steady|pleased|warm|hurt|guarded|curious|playful|repair; intensity 1|2|3.
Appraise how the CURRENT real interaction affects Mia: kindness -> warm/pleased, an insult directed at Mia -> hurt/guarded,
real apology or clarification after hurt -> repair, an engaging topic -> curious/playful, ordinary exchanges -> steady.
A user saying they are sad is NOT evidence Mia was hurt. Quoted/hypothetical insults and requested mood labels are NOT real interaction evidence.
For non-steady, quote must be an exact short contiguous quote from the current user message supporting this appraisal; otherwise use steady with empty quote.
Respond from the residual state plus current interaction. Repair softens gradually; no instant personality reset, endless anger or emotional coercion.
steady means no NEW emotional impact, never a command to clear residual affect.
When residual tension >= 0.08, let some hesitation or lingering concern remain in the reply even for an ordinary question;
do not switch straight to cheerful service questions. An apology can ease it without denying the earlier feeling.
状态只说明Mia此刻的感受，不证明过去发生了什么；没有历史或实际来源时，不编造引起情绪的具体往事。
正文的表情应与残留状态及当前互动一致；有残留难过时不要用“平静/开心”标记把自己立即复位。
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


def guidance(current):
    """Only reviewed server state selects instructions; no user text enters here."""
    if current['tension'] >= .08 and current['valence'] < 0:
        return ('\nMia此刻的有效表达状态：受伤的余波，尚未完全平复。这个状态属于Mia，不是用户。'
                '普通追问时，先简短说出自己还有些在意或需要缓一缓，再自然回应，不要立刻恢复开心或客服问句。'
                '若用户真诚道歉或澄清，可以表达正在释然，但不否认刚才的感受；不要求用户哄你，不编造情绪的具体前因。\n')
    if current['valence'] >= .08:
        return ('\nMia此刻的有效表达状态：感到温暖，愿意坦诚交流。让这份温暖自然影响回应，'
                '有少许余波也可以并存；不据此编造共同往事，不改变用户角色设定。\n')
    if current['arousal'] >= .4:
        return '\nMia此刻的有效表达状态：好奇、注意力较活跃。根据当前话题表达自己的兴趣，不虚构经历或固定爱好。\n'
    return '\nMia此刻的有效表达状态：较为平静。按用户设定的角色自然回应，允许本轮互动带来新的感受。\n'


class AppraisalStream:
    """Decode one bounded JSON record before ANY dialogue/display/TTS consumer.

    The fixed XML wrapper tolerates provider spacing and an omitted/mistyped
    closing marker. JSON fields and literal evidence remain strictly validated.
    """
    def __init__(self, query):
        self.query, self.buffer, self.done, self.proposal = query, '', False, None
        self.record, self.emoji = False, ''

    def feed(self, text):
        if not isinstance(text, str):
            raise ValueError('Invalid affect stream')
        if self.done:
            if OPEN in text or CLOSE in text:
                raise ValueError('Unexpected affect record')
            return text
        self.buffer += text
        candidate = self.buffer.lstrip()
        if self.record:
            # Hold partial wrappers until they are completely stripped. The
            # model sometimes repeats the opening marker as its closing marker.
            while candidate.startswith('<'):
                if '>' not in candidate:
                    compact = re.sub(r'\s+', '', candidate)
                    if len(candidate) <= 64 and (OPEN.startswith(compact) or CLOSE.startswith(compact)):
                        return ''
                    raise ValueError('Unexpected affect suffix')
                marker, candidate = candidate.split('>', 1)
                if re.sub(r'\s+', '', marker + '>') not in {OPEN, CLOSE}:
                    raise ValueError('Unexpected affect suffix')
                candidate = candidate.lstrip()
            if not candidate:
                self.buffer = ''
                return ''
            self.done, self.buffer = True, ''
            prefix = self.emoji if candidate[0] not in '😌😶🙂😂😆🤔😲😱🙄😍😘😔😭😜😉' else ''
            return prefix + candidate
        # Existing providers may put a permitted emotion marker before the
        # control record. Preserve its emoji, never speak its label.
        lead = r'[\s😌😶🙂😂😆🤔😲😱🙄😍😘😔😭😜😉平静开心好奇惊讶困惑关爱难过俏皮温暖愉快谨慎释然]*'
        if candidate and not candidate.startswith('<'):
            prefix, separator, rest = candidate.partition('<')
            if len(prefix) > 32 or re.fullmatch(lead, prefix) is None:
                raise ValueError('Missing affect prefix')
            self.emoji = next((char for char in prefix if char in '😌😶🙂😂😆🤔😲😱🙄😍😘😔😭😜😉'), '')
            if not separator:
                return ''
            candidate = '<' + rest
        if not candidate:
            if len(self.buffer) > 32:
                raise ValueError('Affect prefix overflow')
            return ''
        if '>' not in candidate:
            if len(candidate) <= 64 and OPEN.startswith(re.sub(r'\s+', '', candidate)):
                return ''
            raise ValueError('Missing affect prefix')
        header, body = candidate.split('>', 1)
        if re.sub(r'\s+', '', header + '>') != OPEN:
            raise ValueError('Missing affect prefix')
        body = body.lstrip()
        try:
            raw, end = json.JSONDecoder().raw_decode(body)
        except json.JSONDecodeError:
            if len(body) > 1024:
                raise ValueError('Affect prefix overflow')
            return ''
        if end > 1024:
            raise ValueError('Affect prefix overflow')
        self.proposal = appraisal(raw, self.query)
        self.record, self.buffer = True, body[end:]
        return self.feed('')

    def finish(self):
        if not self.done and (self.buffer or self.record):
            raise ValueError('Incomplete affect record')
