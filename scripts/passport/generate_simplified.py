"""Generate flash-resident, sorted OpenCC t2s tables for the Mia display only."""
import json
from pathlib import Path
import sys


def entries(path):
    for line in path.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            key, values = line.split('\t')
            yield key, values.split(' ')[0]


def generate(source, output):
    lines = ['// Generated from OpenCC 1.1.9, Apache-2.0. See third_party/opencc/README.md.',
             '#pragma once', '#include <cstdint>', 'namespace mia_text {',
             'struct Character { uint32_t from, to; };',
             'struct Phrase { uint32_t first; const char* from; const char* to; };']
    stages = [('kCharacters', 'kPhrases', list(entries(source / 'TSCharacters.txt')),
               list(entries(source / 'TSPhrases.txt'))),
              ('kTaiwanCharacters', 'kTaiwanPhrases',
               [(value, key) for key, value in entries(source / 'TWVariants.txt')],
               list(entries(source / 'TWVariantsRevPhrases.txt')))]
    for char_name, phrase_name, characters, phrases in stages:
        chars = sorted((ord(key), ord(value)) for key, value in characters if key != value)
        phrases.sort(key=lambda pair: (ord(pair[0][0]), -len(pair[0]), pair[0]))
        lines.append(f'inline constexpr Character {char_name}[] = {{')
        lines.extend(f'    {{0x{key:X}, 0x{value:X}}},' for key, value in chars)
        lines.extend(['};', f'inline constexpr Phrase {phrase_name}[] = {{'])
        lines.extend(f'    {{0x{ord(key[0]):X}, {json.dumps(key, ensure_ascii=False)}, {json.dumps(value, ensure_ascii=False)}}},'
                     for key, value in phrases)
        lines.append('};')
    lines.extend(['}  // namespace mia_text', ''])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
