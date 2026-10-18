"""Validate the ESP32-C3 image format, revision limits, checksum and digest."""
import hashlib
import struct


def image_info(data, application=True):
    if len(data) < 32 or data[0] != 0xe9 or not 1 <= data[1] <= 16:
        raise ValueError('invalid ESP image header')
    if struct.unpack_from('<H', data, 12)[0] != 5 or data[3] >> 4 != 3:
        raise ValueError('image must target ESP32-C3 and 8MB flash')
    offset, checksum = 24, 0xef
    for _ in range(data[1]):
        if offset + 8 > len(data):
            raise ValueError('truncated segment header')
        size = struct.unpack_from('<I', data, offset + 4)[0]
        offset += 8
        if not size or size % 4 or size > len(data) - offset:
            raise ValueError('invalid segment length')
        for value in data[offset:offset + size]:
            checksum ^= value
        offset += size
    end = (offset | 15) + 1
    if end > len(data) or data[end - 1] != checksum:
        raise ValueError('ESP image checksum mismatch')
    if data[23] == 1:
        if len(data) != end + 32 or hashlib.sha256(data[:end]).digest() != data[end:]:
            raise ValueError('ESP image appended SHA-256 mismatch')
    elif data[23] != 0 or len(data) != end:
        raise ValueError('unsupported ESP image trailer')
    result = dict(min_revision=max(data[14], struct.unpack_from('<H', data, 15)[0]),
                  max_revision=struct.unpack_from('<H', data, 17)[0])
    if application:
        if len(data) < 288 or struct.unpack_from('<I', data, 32)[0] != 0xabcd5432:
            raise ValueError('missing ESP application descriptor')
        for name, start in [('version', 48), ('project', 80), ('idf', 144)]:
            raw = data[start:start+32]
            if b'\0' not in raw:
                raise ValueError('unterminated ESP descriptor')
            result[name] = raw.split(b'\0', 1)[0].decode('ascii')
        if result['project'] != 'xiaozhi' or not result['idf'].startswith('v6.1'):
            raise ValueError('expected Mia XiaoZhi image built with IDF 6.1')
    return result

