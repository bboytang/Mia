#!/usr/bin/env python3
"""Read-only inventory of a private, full AI Passport flash backup. Never flashes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

FLASH_SIZE = 0x800000
# Historical upstream 50fd39c; these are protected even if the table omits them.
HISTORICAL = {'cardid': (0x356000, 0x4000), 'recovery': (0x700000, 0x100000)}


def partitions(table):
    if len(table) != 0x1000:
        raise ValueError('partition table must be exactly 4096 bytes')
    entries = []
    labels = set()
    for pos in range(0, 0xc00, 32):
        raw = table[pos:pos + 32]
        if raw[:2] == b'\xeb\xeb':
            if raw[2:16] != b'\xff' * 14:
                raise ValueError('invalid partition MD5 marker')
            if hashlib.md5(table[:pos]).digest() != raw[16:]:
                raise ValueError('partition table MD5 mismatch')
            if not entries:
                raise ValueError('empty partition table')
            return entries
        if raw[:2] != b'\xaa\x50':
            raise ValueError('missing valid table/MD5; encrypted or unknown layout needs offline review')
        _, kind, subtype, offset, size, label, flags = struct.unpack('<HBBII16sI', raw)
        label = label.split(b'\0', 1)[0].decode('ascii')
        if not label or label in labels or any(ord(ch) < 32 or ord(ch) > 126 for ch in label):
            raise ValueError('invalid/duplicate partition label')
        if offset < 0x9000 or offset % 0x1000 or not size or size % 0x1000 or offset + size > FLASH_SIZE:
            raise ValueError('partition alignment/bounds invalid')
        if kind == 0 and offset % 0x10000:
            raise ValueError('application alignment invalid')
        if any(offset < p['offset'] + p['size'] and p['offset'] < offset + size for p in entries):
            raise ValueError('overlapping partitions')
        labels.add(label)
        entries.append(dict(label=label, type=kind, subtype=subtype, offset=offset, size=size, flags=flags))
    raise ValueError('missing partition table MD5')


def audit(data):
    if len(data) != FLASH_SIZE:
        raise ValueError('requires a full 8MB backup, not an application/merged build image')
    table = partitions(data[0x8000:0x9000])
    regions = {}
    for label, (offset, size) in HISTORICAL.items():
        chunk = data[offset:offset + size]
        regions[label] = dict(offset=offset, size=size, sha256=hashlib.sha256(chunk).hexdigest(),
                              all_ff=chunk == b'\xff' * size,
                              declared=any(p['label'] == label and p['offset'] == offset and p['size'] == size for p in table))
    return dict(schema=1, flash_bytes=len(data), backup_sha256=hashlib.sha256(data).hexdigest(),
                partitions=table, historical_regions=regions, flash_authorized=False,
                review_required=['Verify actual factory identity/key locations, including NVS, gaps and eFuse.',
                                 'Retain private full backup and review bootloader/Recovery compatibility.',
                                 'An all-FF or undeclared historical region does not prove it is safe to overwrite.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.backup.read_bytes())
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f'audit refused: {exc}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
