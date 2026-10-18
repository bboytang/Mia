import csv
import hashlib
from pathlib import Path
import shlex
import os
import struct
import subprocess
import tempfile
import unittest

from scripts.passport.audit_flash import audit, partitions, FLASH_SIZE
from scripts.passport.build_report import report

ROOT = Path(__file__).resolve().parents[2]


def table(entries):
    data = b''.join(struct.pack('<HBBII16sI', 0x50aa, kind, subtype, offset, size,
                                label.encode(), 0) for kind, subtype, offset, size, label in entries)
    return (data + b'\xeb\xeb' + b'\xff' * 14 + hashlib.md5(data).digest()).ljust(4096, b'\xff')


ORIGINAL = [(1, 2, 0x9000, 0x6000, 'nvs'), (1, 1, 0xf000, 0x1000, 'phy_init'),
            (0, 0, 0x10000, 0x300000, 'factory'),
            (1, 2, 0x356000, 0x4000, 'cardid'), (0, 0x20, 0x700000, 0x100000, 'recovery')]


def candidate():
    types = {'data': 1, 'app': 0}
    subtypes = {'nvs': 2, 'phy': 1, 'ota': 0, 'ota_0': 0x10, 'ota_1': 0x11, 'spiffs': 0x82, 'test': 0x20}
    path = ROOT / 'partitions/mia-passport-8m-candidate.csv'
    rows = csv.reader(line for line in path.read_text().splitlines() if not line.startswith('#'))
    return [(types[r[1].strip()], subtypes[r[2].strip()], int(r[3], 0), int(r[4], 0), r[0].strip()) for r in rows]


class PassportSafetyTests(unittest.TestCase):
    def test_endpoint_policy_accepts_pinned_http_ws_and_rejects_endpoint_changes(self):
        source = r'''
#include "passport/backend_policy.h"
#include <cassert>
int main() {
    using mia::passport::IsPinnedEndpoint;
    using mia::passport::IsDiscoveryEndpoint;
    using mia::passport::IsVoiceEndpoint;
    constexpr auto discovery = "http://43.143.230.174:8002/xiaozhi/ota/";
    constexpr auto voice = "ws://43.143.230.174:8000/xiaozhi/v1/";
    assert(IsDiscoveryEndpoint(discovery, discovery));
    assert(IsVoiceEndpoint(voice, voice));
    assert(!IsDiscoveryEndpoint(discovery, "https://43.143.230.174:8002/xiaozhi/ota/"));
    assert(!IsVoiceEndpoint(voice, "wss://43.143.230.174:8000/xiaozhi/v1/"));
    for (auto url : {"http://xiaozhi.me/xiaozhi/ota/", "http://43.143.230.174:8003/xiaozhi/ota/",
                     "http://43.143.230.174:8002/other/"}) {
        assert(!IsDiscoveryEndpoint(url, discovery));
    }
    assert(!IsVoiceEndpoint("ws://other.example/xiaozhi/v1/", voice));
    assert(!IsVoiceEndpoint("ws://43.143.230.174:8001/xiaozhi/v1/", voice));
    assert(!IsVoiceEndpoint("ws://43.143.230.174:8000/other/", voice));
    assert(!IsDiscoveryEndpoint(voice, voice));
    assert(!IsVoiceEndpoint(discovery, discovery));
    assert(!IsDiscoveryEndpoint("", ""));
    assert(!IsVoiceEndpoint("", ""));
    constexpr auto pin = "https://mia.example:8002/xiaozhi/ota/";
    assert(IsPinnedEndpoint(pin, pin, "https://"));
    assert(IsDiscoveryEndpoint(pin, pin));
    assert(IsVoiceEndpoint("wss://mia.example/v1/", "wss://mia.example/v1/"));
    assert(IsPinnedEndpoint("wss://mia.example/v1/", "wss://mia.example/v1/", "wss://"));
    for (auto url : {"", "http://mia.example:8002/xiaozhi/ota/",
                     "https://xiaozhi.me/ota/", "https://mia.example:8002/other/"}) {
        assert(!IsPinnedEndpoint(url, pin, "https://"));
    }
    for (auto url : {"https:///ota/", "https://user@mia.example/ota/", "https://mia.example/ota/?key=x",
                     "https://mia.example/ota/#x", "https://mia.example/\\evil", "https://mia.example/\n"}) {
        assert(!IsPinnedEndpoint(url, url, "https://"));
    }
    assert(!IsPinnedEndpoint("", "", "https://"));
    for (auto url : {"http:///ota/", "http://user@mia.example/ota/", "http://mia.example/ota/?key=x",
                     "http://mia.example/ota/#x", "http://mia.example/\\evil", "http://mia.example/\n"}) {
        assert(!IsDiscoveryEndpoint(url, url));
    }
    for (auto url : {"ws:///v1/", "ws://user@mia.example/v1/", "ws://mia.example/v1/?key=x",
                     "ws://mia.example/v1/#x", "ws://mia.example/\\evil", "ws://mia.example/\n"}) {
        assert(!IsVoiceEndpoint(url, url));
    }
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'test.cc').write_text(source)
            subprocess.run([*shlex.split(os.environ.get('CXX', 'c++')), '-std=c++20', '-Wall', '-Wextra', '-Werror',
                            '-I', str(ROOT / 'main'), str(path / 'test.cc'), '-o', str(path / 'test')], check=True)
            subprocess.run([str(path / 'test')], check=True)

    def test_original_layout_inventory_exposes_no_identity_payload(self):
        data = bytearray(b'\xff' * FLASH_SIZE)
        data[0x8000:0x9000] = table(ORIGINAL)
        secret = b'PRIVATE-FACTORY-IDENTITY'
        data[0x356000:0x356000 + len(secret)] = secret
        result = audit(data)
        self.assertFalse(result['flash_authorized'])
        self.assertTrue(result['historical_regions']['cardid']['declared'])
        self.assertFalse(result['historical_regions']['cardid']['all_ff'])
        self.assertNotIn(secret.decode(), str(result))

    def test_current_bsp_does_not_imply_historical_regions_are_safe(self):
        data = bytearray(b'\xff' * FLASH_SIZE)
        data[0x8000:0x9000] = table(ORIGINAL[:2] + [(0, 0, 0x10000, 0x7f0000, 'factory')])
        result = audit(data)
        self.assertFalse(result['historical_regions']['cardid']['declared'])
        self.assertFalse(result['flash_authorized'])
        self.assertTrue(result['review_required'])

    def test_reject_incomplete_backup(self):
        with self.assertRaises(ValueError):
            audit(b'\xff' * 4096)

    def test_reject_corrupt_md5(self):
        data = bytearray(table(ORIGINAL))
        data[14] ^= 1
        with self.assertRaisesRegex(ValueError, 'MD5'):
            partitions(data)

    def test_reject_missing_md5(self):
        data = table(ORIGINAL)
        with self.assertRaises(ValueError):
            partitions(data[:160] + b'\xff' * (4096 - 160))

    def test_reject_invalid_bounds_alignment_overlap_duplicate(self):
        for entry in [(1, 2, 0x800000, 0x1000, 'bad'), (1, 2, 0x9001, 0x1000, 'bad'),
                      (1, 2, 0xa000, 0x1000, 'bad'), (1, 2, 0x400000, 0x1000, 'nvs'),
                      (0, 0x10, 0x321000, 0x1000, 'bad')]:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                partitions(table(ORIGINAL + [entry]))

    def test_candidate_preserves_fixed_regions_and_full_original_nvs(self):
        layout = partitions(table(candidate()))
        by_name = {p['label']: p for p in layout}
        for label in ('nvs', 'phy_init', 'cardid', 'recovery'):
            old = next(e for e in ORIGINAL if e[4] == label)
            self.assertEqual((by_name[label]['offset'], by_name[label]['size']), old[2:4])
        self.assertEqual(by_name['ota_0']['size'], by_name['ota_1']['size'])
        self.assertEqual(by_name['assets']['offset'] + by_name['assets']['size'], 0x700000)

    def test_capacity_report_and_reject_wrong_chip_oversize_assets_and_old_idf(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            (build / 'partition_table').mkdir()
            (build / 'partition_table/partition-table.bin').write_bytes(table(candidate()))
            app = bytearray(4096)
            app[0] = 0xe9
            struct.pack_into('<H', app, 12, 5)
            struct.pack_into('<I', app, 32, 0xabcd5432)
            app[144:150] = b'v6.1\x00\x00'
            (build / 'xiaozhi.bin').write_bytes(app)
            (build / 'generated_assets.bin').write_bytes(b'a' * 128)
            result = report(build)
            self.assertEqual(result['application']['bytes'], 4096)
            self.assertEqual(result['assets']['capacity_bytes'], 0xa0000)
            self.assertFalse(result['hardware_verified'])
            self.assertEqual(result['application']['sha256'], hashlib.sha256(app).hexdigest())
            (build / 'generated_assets.bin').write_bytes(b'a' * (0xa0000 + 1))
            with self.assertRaises(ValueError):
                report(build)
            (build / 'generated_assets.bin').write_bytes(b'a')
            for chip, idf in [(9, b'v6.1'), (5, b'v5.5.3'), (5, b'v6.0.0')]:
                struct.pack_into('<H', app, 12, chip)
                app[144:176] = idf.ljust(32, b'\x00')
                (build / 'xiaozhi.bin').write_bytes(app)
                with self.assertRaises(ValueError):
                    report(build)
