#!/usr/bin/env python3
"""Create a new private P-256 release key and matching public source files.

Do not run for a routine release: existing devices trust the existing public key.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

from scripts.passport.sign_release import public_point


def create(private_directory, public_directory):
    public = public_directory / 'release_public_key.pem'
    if public.exists() or (public_directory / 'release_public_key.h').exists():
        raise FileExistsError('refusing to replace an existing firmware trust key')
    private_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = private_directory / 'release-key.pem'
    # openssl inherits this process umask, so the private file is never world-readable.
    import os
    old = os.umask(0o077)
    try:
        subprocess.run(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256',
                        '-out',str(private)], check=True, capture_output=True)
    finally:
        os.umask(old)
    public_directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(['openssl','pkey','-in',str(private),'-pubout','-out',str(public)], check=True, capture_output=True)
    point = public_point(public)
    code = '#pragma once\n\n#include <array>\n#include <cstdint>\n\nnamespace mia::passport {\n'
    code += 'inline constexpr std::array<uint8_t, 65> kReleasePublicKey = {\n    '
    code += ', '.join(f'0x{b:02x}' for b in point) + '\n};\n}  // namespace mia::passport\n'
    (public_directory / 'release_public_key.h').write_text(code)
    return hashlib.sha256(point).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-directory', type=Path, required=True)
    parser.add_argument('--public-directory', type=Path, required=True)
    args = parser.parse_args()
    try:
        fingerprint = create(args.private_directory, args.public_directory)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'key creation failed: {type(exc).__name__}\n')
    print('Public key SHA-256: '+fingerprint)
    print('Keep the private key offline; it is required for future OTA releases.')


if __name__ == '__main__':
    main()
