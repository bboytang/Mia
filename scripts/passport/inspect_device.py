#!/usr/bin/env python3
"""Read chip/security metadata and the 4KiB partition table only. Never writes flash.

Run on a USB host with esptool 5+ installed; not an Android USB compatibility claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def summary(log, table):
    from scripts.passport.audit_flash import partitions
    layout = partitions(table)
    revision = re.search(r'revision\s+v(\d+)\.(\d+)', log, re.I)
    def enabled(label):
        matches = {v.lower() for v in re.findall(r'^\s*'+label+r':\s*(Enabled|Disabled)\s*$', log, re.I | re.M)}
        return None if len(matches) != 1 else matches.pop() == 'enabled'
    return dict(chip='esp32c3' if 'ESP32-C3' in log else None,
                flash_bytes=0x800000 if re.search(r'Detected flash size:\s*8\s*MB', log, re.I) else None,
                chip_revision=int(revision[1])*100+int(revision[2]) if revision else None,
                secure_boot=enabled('Secure Boot'), flash_encryption=enabled('Flash Encryption'),
                partition_table_sha256=hashlib.sha256(table).hexdigest(), partitions=layout,
                identity_regions_reviewed=False, recovery_boot_change_noted=False,
                flash_authorized=False, full_flash_backup_read=False)


def inspect(port, output):
    # A new private directory avoids mixing observations from different devices.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    base = [sys.executable, '-m', 'esptool', '--chip', 'esp32c3', '--port', port,
            '--baud', '115200', '--after', 'no-reset']
    logs = []
    for action in (['flash-id'], ['get-security-info'],
                   ['read-flash', '0x8000', '0x1000', str(output / 'partition-table.bin')]):
        result = subprocess.run(base + action, capture_output=True, text=True, timeout=120, check=True)
        logs.append(result.stdout + result.stderr)
    log = '\n'.join(logs)
    (output / 'readonly-probe.log').write_text(log)
    report = summary(log, (output / 'partition-table.bin').read_bytes())
    (output / 'device-review.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def import_browser(path, output):
    """Import a local non-secret browser readout; never treat it as approval."""
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or data.get('source') != 'mia-passport-browser-inspection':
        raise ValueError('unrecognized browser inspection report')
    raw = data.get('partition_table_hex')
    if not isinstance(raw, str) or len(raw) != 8192:
        raise ValueError('expected exactly 4KiB partition table')
    table = bytes.fromhex(raw)
    from scripts.passport.audit_flash import partitions
    layout = partitions(table)
    if hashlib.sha256(table).hexdigest() != data.get('partition_table_sha256'):
        raise ValueError('browser partition table hash mismatch')
    keys = ('chip', 'flash_bytes', 'chip_revision', 'secure_boot', 'flash_encryption',
            'partition_table_sha256')
    report = {key: data.get(key) for key in keys}
    report.update(partitions=layout, identity_regions_reviewed=False,
                  recovery_boot_change_noted=False, flash_authorized=False, full_flash_backup_read=False)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    (output / 'partition-table.bin').write_bytes(table)
    (output / 'device-review.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--port')
    source.add_argument('--browser-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = import_browser(args.browser_report, args.output) if args.browser_report else inspect(args.port, args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f'read-only inspection failed: {type(exc).__name__}; no flash writes were requested\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
