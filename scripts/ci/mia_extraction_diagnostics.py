"""Bounded original SDK fields for P23 extraction diagnosis, never response repair."""

import hashlib
import json


MAX_CAPTURE_BYTES = 1024 * 1024
MAX_CAPTURE_FRAMES = 8192


class StreamCapture:
    def __init__(self, request_number, kwargs):
        raw = json.dumps(kwargs, ensure_ascii=False, sort_keys=True).encode()
        self.entry = {'request_number': request_number, 'request_sha256': hashlib.sha256(raw).hexdigest(),
            'request_bytes': len(raw), 'request_truncated': len(raw) > MAX_CAPTURE_BYTES,
            'request': json.loads(raw) if len(raw) <= MAX_CAPTURE_BYTES else None,
            'parts': [], 'parts_seen': 0, 'captured_bytes': 0, 'capture_truncated': False,
            'scope': 'Exact SDK fields consumed by original Provider/read_stream, not raw wire SSE; no reconstructed/repaired proposal'}
        self.digest = hashlib.sha256()

    def append(self, chunk):
        choices = getattr(chunk, 'choices', None) or []
        if choices:
            delta = choices[0].delta
            calls = getattr(delta, 'tool_calls', None)
            part = {'has_choice': True, 'content': getattr(delta, 'content', None),
                'finish_reason': getattr(choices[0], 'finish_reason', None),
                'tool_calls': None if calls is None else [
                    {'index': call.index, 'id': call.id, 'type': getattr(call, 'type', None),
                        'function': None if call.function is None else
                            {'name': call.function.name, 'arguments': call.function.arguments}} for call in calls]}
        else:
            part = {'has_choice': False}
        raw = json.dumps(part, ensure_ascii=False, sort_keys=True).encode()
        self.digest.update(raw + b'\n')
        self.entry['parts_seen'] += 1
        if (not self.entry['capture_truncated'] and len(self.entry['parts']) < MAX_CAPTURE_FRAMES
                and self.entry['captured_bytes'] + len(raw) <= MAX_CAPTURE_BYTES):
            self.entry['parts'].append(part)
            self.entry['captured_bytes'] += len(raw)
        else:
            self.entry['capture_truncated'] = True

    def finish(self):
        self.entry['consumed_parts_sha256'] = self.digest.hexdigest()
