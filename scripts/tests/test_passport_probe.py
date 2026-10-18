import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.passport.create_signing_key import create
from scripts.passport.inspect_device import inspect, summary
from scripts.passport.sign_release import public_point
from scripts.tests.test_passport_safety import table, ORIGINAL

LOG = '''Chip type: ESP32-C3 (revision v0.4)
Detected flash size: 8MB
Secure Boot: Disabled
Flash Encryption: Disabled
'''


class PassportProbeTests(unittest.TestCase):
    def test_read_only_metadata_is_not_automatically_authorized(self):
        result = summary(LOG, table(ORIGINAL))
        self.assertEqual(result['chip_revision'],4)
        self.assertEqual(result['flash_bytes'],0x800000)
        self.assertIs(result['secure_boot'],False)
        self.assertFalse(result['identity_regions_reviewed'])
        self.assertFalse(result['flash_authorized'])
        self.assertFalse(result['full_flash_backup_read'])

    def test_unknown_or_conflicting_security_information_is_not_treated_as_disabled(self):
        self.assertIsNone(summary('',table(ORIGINAL))['secure_boot'])
        self.assertIsNone(summary(LOG+'Secure Boot: Enabled\n',table(ORIGINAL))['secure_boot'])
        self.assertTrue(summary(LOG.replace('Secure Boot: Disabled','Secure Boot: Enabled'),table(ORIGINAL))['secure_boot'])

    def test_probe_issues_only_three_read_only_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'probe'
            def run(command, **kwargs):
                if 'read-flash' in command:
                    self.assertEqual(command[-3:-1],['0x8000','0x1000'])
                    Path(command[-1]).write_bytes(table(ORIGINAL))
                return SimpleNamespace(stdout=LOG,stderr='')
            with patch('scripts.passport.inspect_device.subprocess.run', side_effect=run) as mocked:
                inspect('/dev/test-port',output)
            self.assertEqual(mocked.call_count,3)
            commands = [call.args[0] for call in mocked.call_args_list]
            self.assertTrue(any('flash-id' in command for command in commands))
            self.assertTrue(any('get-security-info' in command for command in commands))
            self.assertFalse(any(word in ('write-flash','erase-flash','write-mem','burn-key') for command in commands for word in command))
            self.assertEqual((output/'partition-table.bin').stat().st_size,4096)

    def test_key_generation_never_replaces_existing_trust_key(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            fingerprint = create(path/'private',path/'public')
            self.assertEqual(fingerprint,hashlib.sha256(public_point(path/'public/release_public_key.pem')).hexdigest())
            self.assertEqual((path/'private/release-key.pem').stat().st_mode & 0o777,0o600)
            self.assertIn('kReleasePublicKey',(path/'public/release_public_key.h').read_text())
            with self.assertRaises(FileExistsError):
                create(path/'other-private',path/'public')
            self.assertFalse((path/'other-private').exists())
