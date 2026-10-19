#!/usr/bin/env python3
"""Pair actual LVGL RGB565 captures with unmodified reference crops (host only)."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat


def compare(renders, references, output):
    output.mkdir(parents=True, exist_ok=True)
    pairs = []
    overview = Image.new('RGB', (4 * 496, 3 * 352), '#101624')
    records = []
    for i, reference in enumerate(sorted(references.glob('[0-9][0-9]_*.png'))):
        n = i + 1
        actual_file = renders / f'{n:02d}.ppm'
        actual = Image.open(actual_file).convert('RGB')
        target = Image.open(reference).convert('RGB')
        if actual.size != (240, 320) or target.size != (240, 320):
            raise ValueError('Native screenshots and references must be exactly 240x320')
        actual.save(output / f'{n:02d}-implementation.png')
        pair = Image.new('RGB', (496, 352), '#101624')
        d = ImageDraw.Draw(pair)
        d.text((8, 6), f'{n:02d} REFERENCE', fill='white')
        d.text((256, 6), 'LVGL RGB565 / HOST', fill='white')
        pair.paste(target, (4, 28))
        pair.paste(actual, (252, 28))
        pair.save(output / f'{n:02d}-comparison.png')
        overview.paste(pair, (i % 4 * 496, i // 4 * 352))
        stat = ImageStat.Stat(ImageChops.difference(actual, target))
        records.append(dict(screen=reference.stem, rgb_mae=round(sum(stat.mean) / 3, 3),
                            implementation_sha256=hashlib.sha256(actual_file.read_bytes()).hexdigest(),
                            reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest()))
    if len(records) != 12:
        raise ValueError(f'Expected 12 screens, found {len(records)}')
    overview.save(output / 'all-12-comparison.png')
    report = dict(renderer='Production Painter with LVGL 9.5.0, RGB565, 20-row strip, 32KB pool',
                  hardware_tested=False, fixture_data=True,
                  note='MAE is descriptive, not a 1:1 acceptance score. References include cropped device borders and simulated glows. Screen 09 deliberately uses a full ASCII selector; Home_5G is replaced by a 2.4GHz fixture.',
                  host_metrics=json.loads((renders / 'host-metrics.json').read_text()), screens=records)
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('renders', type=Path)
    parser.add_argument('references', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    compare(args.renders, args.references, args.output)
