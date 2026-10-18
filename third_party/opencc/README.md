# OpenCC dictionary data

Unmodified `TSCharacters.txt`, `TSPhrases.txt`, `TWVariants.txt`,
`TWVariantsRevPhrases.txt` and `LICENSE` from OpenCC 1.1.9:
https://github.com/BYVoid/OpenCC/tree/556ed22496d650bd0b13b6c163be9814637970ae

Copyright OpenCC contributors. Licensed under Apache-2.0; see LICENSE.
These data files are used under that license, not copied as documentation.

`scripts/passport/generate_simplified.py` derives sorted C++ constexpr tables
in the build directory, using each entry's first candidate. Mia's display uses
Taiwan variant normalization, followed by longest phrase matching and character mapping, preserving contextual forms
such as 乾坤. Tables stay in flash; only the resulting subtitle is allocated.
This applies OpenCC's tw2s dictionary stages with longest matching,
not regional vocabulary rewriting (e.g. Taiwan-specific terminology).
It does not change backend transcripts, dialogue memory, TTS or other boards.
