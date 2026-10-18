#!/usr/bin/env python3
"""Report candidate capacity only; produces no flashable package or release manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def measure(path, capacity):
    data = path.read_bytes()
    if not data or len(data) > capacity:
        raise ValueError(f'{path.name} is empty or exceeds candidate partition ({len(data)}/{capacity})')
    return dict(bytes=len(data), capacity_bytes=capacity, usage_percent=round(100 * len(data) / capacity, 2),
                remaining_bytes=capacity - len(data), sha256=hashlib.sha256(data).hexdigest())


def report(build):
    app = build / 'xiaozhi.bin'
    data = app.read_bytes()
    if len(data) < 288 or data[0] != 0xe9 or struct.unpack_from('<H', data, 12)[0] != 5:
        raise ValueError('not an ESP32-C3 application image')
    if struct.unpack_from('<I', data, 32)[0] != 0xabcd5432:
        raise ValueError('missing application descriptor')
    version = data[144:176].split(b'\0', 1)[0].decode('ascii')
    if not (version.startswith('v6.1') or version.startswith('v6.0.') and
            int(version[5:].split('-')[0]) >= 1):
        raise ValueError('requires IDF >= 6.0.1; recommended v6.1')
    # Read the actual generated table, not just assumed capacities.
    from scripts.passport.audit_flash import partitions
    table = partitions((build / 'partition_table/partition-table.bin').read_bytes().ljust(4096, b'\xff'))
    slots = [p for p in table if p['type'] == 0 and p['subtype'] in (0x10, 0x11)]
    if len(slots) != 2 or slots[0]['size'] != slots[1]['size']:
        raise ValueError('requires two equal A/B slots')
    assets = next(p for p in table if p['label'] == 'assets')
    return dict(schema=1, status='development-only-not-approved-for-flashing', idf_version=version,
                application=measure(app, min(p['size'] for p in slots)),
                assets=measure(build / 'generated_assets.bin', assets['size']), partitions=table,
                signature_included=False, hardware_verified=False,
                release_blockers=['Factory flash audit and migration approval',
                                 'Signed OTA, trial boot health check, rollback fault injection',
                                 'TLS endpoint and device binding integration'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    args = parser.parse_args()
    try:
        result = report(args.build)
    except (ValueError, OSError, StopIteration, UnicodeError) as exc:
        parser.exit(2, f'capacity check failed: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
