import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

from scripts.passport.package_release import image_info, review_device, make_package, FACTORY_RESOURCES
from scripts.passport.sign_release import public_point, sign
from scripts.tests.test_passport_safety import candidate, ORIGINAL, table


def image(public, version='1.0.0'):
    header = bytearray(24)
    header[0] = 0xe9
    header[1] = 1
    header[3] = 0x30
    header[23] = 1
    struct.pack_into('<H', header, 12, 5)
    payload = bytearray(512)
    struct.pack_into('<I', payload, 0, 0xabcd5432)
    payload[16:48] = version.encode().ljust(32, b'\0')
    payload[48:80] = b'xiaozhi'.ljust(32, b'\0')
    payload[112:144] = b'v6.1'.ljust(32, b'\0')
    payload[300:365] = public
    result = header + struct.pack('<II', 0x3c000020, len(payload)) + payload
    checksum = 0xef
    for value in payload:
        checksum ^= value
    result += b'\0' * ((len(result) | 15) - len(result)) + bytes([checksum])
    return bytes(result) + hashlib.sha256(result).digest()


class PassportPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.private = self.path / 'private.pem'
        self.public = self.path / 'public.pem'
        subprocess.run(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(self.private)], check=True, capture_output=True)
        subprocess.run(['openssl','pkey','-in',str(self.private),'-pubout','-out',str(self.public)], check=True, capture_output=True)
        self.app = image(public_point(self.public))
        self.device_table = table(ORIGINAL)
        self.review = dict(chip='esp32c3', flash_bytes=0x800000, chip_revision=4,
                           secure_boot=False, flash_encryption=False,
                           identity_regions_reviewed=True, recovery_boot_change_noted=True,
                           partition_table_sha256=hashlib.sha256(self.device_table).hexdigest())
        self.build = self.path / 'build'
        (self.build / 'bootloader').mkdir(parents=True)
        (self.build / 'partition_table').mkdir()
        (self.build / 'xiaozhi.bin').write_bytes(self.app)
        (self.build / 'bootloader/bootloader.bin').write_bytes(self.app)
        (self.build / 'partition_table/partition-table.bin').write_bytes(table(candidate()))
        (self.build / 'generated_assets.bin').write_bytes(b'fonts-and-expressions')
        self.output = self.path / 'release.zip'

    def package(self):
        return make_package(self.build, self.device_table, self.review, self.private, self.public, 1, self.output)

    def test_segmented_package_preserves_factory_regions_and_excludes_private_key(self):
        result = self.package()
        self.assertFalse(result['erase_all'])
        self.assertFalse(result['flash_authorized'])
        self.assertTrue(result['first_flash_requires_explicit_owner_confirmation'])
        self.assertEqual([p['offset'] for p in result['segments']], [0,0x8000,0x10000,0x20000,0x660000])
        with zipfile.ZipFile(self.output) as archive:
            self.assertNotIn('merged-binary.bin', archive.namelist())
            self.assertFalse(any('private' in f or 'cardid.bin' in f or 'recovery.bin' in f for f in archive.namelist()))
            self.assertEqual(len(archive.read('usb/assets.bin')), 0xa0000)
            self.assertEqual(archive.read('usb/otadata-initial.bin'), b'\xff'*0x2000)
            self.assertTrue(archive.read(result['ota']['file']).startswith(b'MIAOTA1\0'))
            ota = json.loads(archive.read(result['ota']['manifest_file']))
            self.assertEqual(ota['capsule_sha256'], result['ota']['sha256'])
            self.assertEqual(ota['image_sha256'], hashlib.sha256(self.app).hexdigest())
            self.assertFalse(ota['usb_flashable'])
            self.assertTrue(archive.read('usb/mia-ai-passport.bin').startswith(b'\xe9'))
            for segment in result['segments']:
                self.assertEqual(hashlib.sha256(archive.read(segment['file'])).hexdigest(), segment['sha256'])
                for region in result['protected']:
                    self.assertFalse(segment['erase_start'] < region['offset']+region['bytes'] and region['offset'] < segment['erase_start']+segment['erase_bytes'])

    def test_image_integrity_and_chip_checks(self):
        self.assertEqual(image_info(self.app)['version'], '1.0.0')
        for offset in (0,12,32,350,len(self.app)-1):
            bad = bytearray(self.app); bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                image_info(bad)
        with self.assertRaises(ValueError):
            image_info(self.app[:-1])
        with self.assertRaises(ValueError):
            image_info(self.app + b'x')

    def test_no_package_without_matching_review_and_security_state(self):
        good = copy.deepcopy(self.review)
        for field, value in [('partition_table_sha256','wrong'),('chip','esp32s3'),('flash_bytes',0x400000),
                             ('secure_boot',True),('flash_encryption',True),('secure_boot',None),
                             ('chip_revision',None),('identity_regions_reviewed',False),('recovery_boot_change_noted',False)]:
            with self.subTest(field=field):
                self.review = {**good, field:value}
                with self.assertRaises(ValueError):
                    self.package()
                self.assertFalse(self.output.exists())

    def test_unknown_factory_layout_is_not_assumed_blank(self):
        current = table(ORIGINAL[:2] + [(0,0,0x10000,0x7f0000,'factory')])
        review = {**self.review, 'partition_table_sha256':hashlib.sha256(current).hexdigest()}
        with self.assertRaisesRegex(ValueError,'unrecognized'):
            review_device(current, review)

    def test_device_resource_layout_needs_separate_owner_decision(self):
        entries = ORIGINAL[:-1] + [(1, 0x82, address, size, label)
                                  for label, (address, size) in FACTORY_RESOURCES.items()]
        self.device_table = table(sorted(entries, key=lambda p: p[2]))
        self.review['partition_table_sha256'] = hashlib.sha256(self.device_table).hexdigest()
        for value in (None, False, 'true'):
            self.review['factory_resources_discard_approved'] = value
            with self.assertRaisesRegex(ValueError, 'explicit owner decision'):
                self.package()
            self.assertFalse(self.output.exists())
        self.review['factory_resources_discard_approved'] = True
        result = self.package()
        self.assertEqual({p['label'] for p in result['retired_factory_resources']}, set(FACTORY_RESOURCES))
        self.assertFalse(result['flash_authorized'])
        self.assertFalse(result['recovery_boot_hook_preserved'])
        self.assertIn(dict(offset=0x700000, bytes=0x100000, label='recovery'), result['protected'])

    def test_resource_discard_decision_cannot_approve_unknown_ranges_or_types(self):
        entries = ORIGINAL[:-1] + [(1, 0x82, address, size, label)
                                  for label, (address, size) in FACTORY_RESOURCES.items()]
        index = next(i for i, p in enumerate(entries) if p[4] == 'imgava')
        for changed in [(1,0x82,0x3fa000,0xff000,'imgava'),
                        (1,2,0x3fa000,0x100000,'imgava'),
                        (1,0x82,0x3fa000,0x100000,'unknown')]:
            altered = entries.copy(); altered[index] = changed
            raw = table(sorted(altered, key=lambda p: p[2]))
            review = {**self.review, 'factory_resources_discard_approved': True,
                      'partition_table_sha256': hashlib.sha256(raw).hexdigest()}
            with self.assertRaises(ValueError):
                review_device(raw, review)

    def test_original_four_partition_revision_still_protects_recovery_address(self):
        old = table(ORIGINAL[:-1])
        review = {**self.review, 'partition_table_sha256':hashlib.sha256(old).hexdigest()}
        regions = review_device(old, review)
        self.assertIn((0x700000,0x100000,'recovery'), regions)

    def test_invalid_artifact_is_not_packaged(self):
        (self.build / 'xiaozhi.bin').write_bytes(self.app[:-1])
        with self.assertRaises(ValueError):
            self.package()
        self.assertFalse(self.output.exists())

    def test_mismatched_signing_key_is_rejected(self):
        other = self.path / 'other.pem'
        subprocess.run(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(other)], check=True, capture_output=True)
        with self.assertRaises(subprocess.CalledProcessError):
            sign(self.app, table(candidate()), b'fonts', 1, other, self.public)
        with self.assertRaises(ValueError):
            sign(image(b'x'*65), table(candidate()), b'fonts', 1, self.private, self.public)

    def test_existing_package_is_never_overwritten(self):
        self.package()
        original = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.package()
        self.assertEqual(self.output.read_bytes(), original)
