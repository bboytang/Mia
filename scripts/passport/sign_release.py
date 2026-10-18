#!/usr/bin/env python3
"""Sign an OTA capsule for the existing XiaoZhi .bin upload/download path.

The 256-byte MIAOTA1 prefix is not an ESP application: never flash this file by USB.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

HEADER_SIZE = 256
SIGNED_SIZE = 192
SLOT_SIZE = 0x300000
ASSETS_SIZE = 0xa0000
BOARD = 'mia-ai-passport'
ROOT = Path(__file__).resolve().parents[2]


def public_point(public_key):
    result = subprocess.run(['openssl', 'pkey', '-pubin', '-in', str(public_key), '-outform', 'DER'],
                            check=True, capture_output=True).stdout
    prefix = bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d030107034200')
    if len(result) != 91 or not result.startswith(prefix) or result[26] != 4:
        raise ValueError('release key must be uncompressed ECDSA P-256')
    return result[26:]


def raw_signature(der):
    if len(der) < 8 or der[0] != 0x30 or der[1] != len(der) - 2:
        raise ValueError('expected a DER ECDSA P-256 signature')
    values = []
    pos = 2
    for _ in range(2):
        if der[pos] != 2:
            raise ValueError('invalid ECDSA signature')
        size = der[pos + 1]
        value = der[pos + 2:pos + 2 + size]
        if size not in range(1, 34) or len(value) != size or value[0] & 0x80:
            raise ValueError('invalid ECDSA integer')
        number = int.from_bytes(value, 'big')
        if not 0 < number < 2**256:
            raise ValueError('invalid P-256 integer')
        values.append(number.to_bytes(32, 'big'))
        pos += 2 + size
    if pos != len(der):
        raise ValueError('trailing signature data')
    return b''.join(values)


def metadata(app, table, assets, sequence):
    if len(app) < 288 or len(app) > SLOT_SIZE or app[0] != 0xe9 or struct.unpack_from('<H', app, 12)[0] != 5:
        raise ValueError('expected a raw ESP32-C3 application fitting 3MiB')
    if struct.unpack_from('<I', app, 32)[0] != 0xabcd5432:
        raise ValueError('missing ESP application descriptor')
    version = app[48:80].split(b'\0', 1)[0].decode('ascii')
    if not version or len(version) > 31 or any(not part.isascii() or not part.isdigit() for part in version.split('.')):
        raise ValueError('version must contain dot-separated decimal integers')
    if not 1 <= sequence <= 0x7fffffff:
        raise ValueError('sequence must be a positive 31-bit integer')
    if not 32 <= len(table) <= 4096 or not assets or len(assets) > ASSETS_SIZE:
        raise ValueError('invalid partition table or assets size')
    from scripts.passport.audit_flash import partitions
    layout = {p['label']: p for p in partitions(table.ljust(4096, b'\xff'))}
    expected = {'ota_0': (0x20000, SLOT_SIZE), 'ota_1': (0x360000, SLOT_SIZE),
                'cardid': (0x356000, 0x4000), 'recovery': (0x700000, 0x100000),
                'assets': (0x660000, ASSETS_SIZE)}
    if any(name not in layout or (layout[name]['offset'], layout[name]['size']) != region for name, region in expected.items()):
        raise ValueError('partition layout does not match the supported Passport layout')
    header = bytearray(SIGNED_SIZE)
    struct.pack_into('<8s6I', header, 0, b'MIAOTA1\0', 1, len(app), sequence, 0x800000, 5, 0)
    header[32:64] = BOARD.encode().ljust(32, b'\0')
    header[64:96] = version.encode().ljust(32, b'\0')
    header[96:128] = hashlib.sha256(app).digest()
    header[128:160] = hashlib.sha256(table.ljust(4096, b'\xff')).digest()
    header[160:192] = hashlib.sha256(assets.ljust(ASSETS_SIZE, b'\xff')).digest()
    return bytes(header), version


def sign(app, table, assets, sequence, private_key, public_key):
    header, version = metadata(app, table, assets, sequence)
    if public_point(public_key) not in app:
        raise ValueError('application does not embed this release public key')
    with tempfile.TemporaryDirectory(prefix='mia-ota-sign-') as temp:
        path = Path(temp)
        (path / 'metadata').write_bytes(header)
        subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(private_key), '-out', str(path / 'signature'),
                        str(path / 'metadata')], check=True, capture_output=True)
        subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(public_key), '-signature', str(path / 'signature'),
                        str(path / 'metadata')], check=True, capture_output=True)
        signature = raw_signature((path / 'signature').read_bytes())
    return header + signature + app, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('app', 'partition-table', 'assets', 'private-key', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--public-key', type=Path, default=ROOT / 'main/passport/release_public_key.pem')
    parser.add_argument('--sequence', type=int, required=True)
    args = parser.parse_args()
    try:
        data, version = sign(args.app.read_bytes(), args.partition_table.read_bytes(), args.assets.read_bytes(),
                             args.sequence, args.private_key, args.public_key)
        # Never silently overwrite an existing release.
        with args.output.open('xb') as target:
            target.write(data)
        manifest = dict(schema=1, board=BOARD, version=version, sequence=args.sequence,
                        format='MIAOTA1-prefix-v1', capsule_bytes=len(data),
                        capsule_sha256=hashlib.sha256(data).hexdigest(), image_bytes=len(data)-HEADER_SIZE,
                        image_sha256=hashlib.sha256(data[HEADER_SIZE:]).hexdigest(),
                        usb_flashable=False)
        args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'release signing failed: {type(exc).__name__}\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
