#!/usr/bin/env python3
"""Create a segmented USB review package only after a device layout/security review.

Does not open a serial port, erase flash, or write a device. No full backup is required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from scripts.passport.audit_flash import partitions, HISTORICAL
from scripts.passport.sign_release import sign, ASSETS_SIZE
from scripts.passport.image_format import image_info

# Factory resource layout observed in the owner's read-only device report.
# Exact ranges only: an additional/moved partition still requires a new review.
FACTORY_RESOURCES = {
    'imgstore': (0x310000, 0x20000),
    'imgframe': (0x330000, 0x26000),
    'imguser': (0x35a000, 0x20000),
    'audio': (0x37a000, 0x80000),
    'imgava': (0x3fa000, 0x100000),
}


def review_device(table, review):
    if len(table) != 4096 or review.get('partition_table_sha256') != hashlib.sha256(table).hexdigest():
        raise ValueError('device table does not match the reviewed readout')
    if review.get('chip') != 'esp32c3' or review.get('flash_bytes') != 0x800000:
        raise ValueError('device must be ESP32-C3 with 8MB flash')
    if review.get('secure_boot') is not False or review.get('flash_encryption') is not False:
        raise ValueError('unknown/enabled chip security needs a separate migration review')
    if type(review.get('chip_revision')) is not int or not 0 <= review['chip_revision'] <= 65535:
        raise ValueError('missing verified chip revision')
    if review.get('identity_regions_reviewed') is not True or review.get('recovery_boot_change_noted') is not True:
        raise ValueError('identity region and bootloader/Recovery review required')
    existing = {p['label']: p for p in partitions(table)}
    known = {'nvs': (0x9000, 0x6000), 'phy_init': (0xf000, 0x1000),
             'factory': (0x10000, 0x300000), 'cardid': HISTORICAL['cardid']}
    resources = set(existing) == set(known) | set(FACTORY_RESOURCES)
    if not resources and set(existing) not in (set(known), set(known) | {'recovery'}):
        raise ValueError('unrecognized factory layout: do not assume hidden data may be overwritten')
    if resources and review.get('factory_resources_discard_approved') is not True:
        raise ValueError('explicit owner decision to discard factory image/avatar/audio resources required')
    ranges = {**known, **(FACTORY_RESOURCES if resources else {}),
              **({'recovery': HISTORICAL['recovery']} if 'recovery' in existing else {})}
    for label, region in ranges.items():
        if (existing[label]['offset'], existing[label]['size']) != region:
            raise ValueError('factory partition moved or resized: needs separate migration review')
        expected = (0, 0) if label == 'factory' else (0, 0x20) if label == 'recovery' else (1, 1) if label == 'phy_init' else (1, 0x82) if label in FACTORY_RESOURCES else (1, 2)
        if (existing[label]['type'], existing[label]['subtype']) != expected or existing[label]['flags'] != 0:
            raise ValueError('unexpected factory partition type or flags')
    return [(0x9000, 0x6000, 'nvs'), (0xf000, 0x1000, 'phy_init'),
            (0x356000, 0x4000, 'cardid'), (0x700000, 0x100000, 'recovery')]


def make_package(build, device_table, review, private_key, public_key, sequence, output):
    protected = review_device(device_table, review)  # No output files before review succeeds.
    app = (build / 'xiaozhi.bin').read_bytes()
    boot = (build / 'bootloader/bootloader.bin').read_bytes()
    table = (build / 'partition_table/partition-table.bin').read_bytes()
    assets = (build / 'generated_assets.bin').read_bytes()
    info = image_info(app)
    loader = image_info(boot, application=False)
    for image in (info, loader):
        if not image['min_revision'] <= review['chip_revision'] or (image['max_revision'] not in (0, 65535) and review['chip_revision'] > image['max_revision']):
            raise ValueError('device silicon revision is incompatible with this image')
    if len(boot) > 0x8000:
        raise ValueError('bootloader overlaps the partition table')
    capsule, version = sign(app, table, assets, sequence, private_key, public_key)
    # Explicitly initialize the entire assets area, including its signed FF tail.
    segments = [(0, 'usb/bootloader.bin', boot),
                (0x8000, 'usb/partition-table.bin', table.ljust(4096, b'\xff')),
                (0x10000, 'usb/otadata-initial.bin', b'\xff' * 0x2000),
                (0x20000, 'usb/mia-ai-passport.bin', app),
                (0x660000, 'usb/assets.bin', assets.ljust(ASSETS_SIZE, b'\xff'))]
    plan = []
    previous_end = 0
    for address, name, data in segments:
        erase_start = address & ~4095
        erase_end = (address + len(data) + 4095) & ~4095
        if address < previous_end or erase_end > 0x800000:
            raise ValueError('overlapping or out-of-bounds image segments')
        for start, size, label in protected:
            if erase_start < start + size and start < erase_end:
                raise ValueError(f'segment erases protected {label}')
        previous_end = erase_end
        plan.append(dict(file=name, offset=address, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                         erase_start=erase_start, erase_bytes=erase_end-erase_start))
    manifest = dict(schema=1, board='mia-ai-passport', version=version, sequence=sequence,
                    device_review=review, segments=plan,
                    protected=[dict(offset=a, bytes=n, label=l) for a,n,l in protected],
                    erase_all=False, flash_authorized=False, hardware_verified=False,
                    first_flash_requires_explicit_owner_confirmation=True,
                    recovery_boot_hook_preserved=False,
                    ota=dict(file=f'ota/mia-ai-passport_{version}.bin', bytes=len(capsule),
                             manifest_file=f'ota/mia-ai-passport_{version}.manifest.json',
                             sha256=hashlib.sha256(capsule).hexdigest(), usb_flashable=False))
    retired = [p for p in partitions(device_table) if p['label'] in FACTORY_RESOURCES]
    if retired:
        manifest['factory_resources_discard_approved'] = True  # review_device enforced it.
        manifest['retired_factory_resources'] = retired
    notes = ('This is a segmented installation review package, not a merged image.\n'
             'No device write is authorized or executed by this package.\n'
             'Obtain explicit owner confirmation before first USB write. Never erase all flash.\n'
             'Use only the USB files at the offsets in flash-plan.json; never USB-flash the OTA capsule.\n'
             'NVS, PHY, cardid and Recovery bytes must remain untouched.\n'
             'The original Recovery key boot hook is not preserved by the IDF6 bootloader.\n'
             'After initial setup, perform a real authenticated voice session to establish the baseline OTA slot.\n'
             'Confirm hardware, then test forward OTA and failure rollback before treating this as production.\n')
    if retired:
        notes += ('Owner accepted retirement of factory image/avatar/audio resource partitions.\n'
                  'These resources are unavailable in Mia; future OTA may overwrite their bytes.\n'
                  'This decision does not authorize the first USB write.\n')
    with output.open('xb') as target:
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('flash-plan.json', json.dumps(manifest, indent=2)+'\n')
            archive.writestr('READ-BEFORE-FLASH.txt', notes)
            for _, name, data in segments:
                archive.writestr(name, data)
            archive.writestr(manifest['ota']['file'], capsule)
            ota_manifest = dict(schema=1, board='mia-ai-passport', version=version, sequence=sequence,
                                format='MIAOTA1-prefix-v1', capsule_bytes=len(capsule),
                                capsule_sha256=hashlib.sha256(capsule).hexdigest(), image_bytes=len(app),
                                image_sha256=hashlib.sha256(app).hexdigest(), usb_flashable=False)
            archive.writestr(manifest['ota']['manifest_file'], json.dumps(ota_manifest, indent=2)+'\n')
            archive.writestr('ota/release-public-key.pem', public_key.read_bytes())
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'device-table', 'device-review', 'private-key', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--public-key', type=Path, default=Path('main/passport/release_public_key.pem'))
    parser.add_argument('--sequence', type=int, required=True)
    args = parser.parse_args()
    try:
        make_package(args.build, args.device_table.read_bytes(), json.loads(args.device_review.read_text()),
                     args.private_key, args.public_key, args.sequence, args.output)
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'package refused: {exc}\n')
    print('Review package created. No device writes authorized or executed.')


if __name__ == '__main__':
    main()
