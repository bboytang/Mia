"""Preview/apply a checked music-selection fix to the v0.9.7 plugin."""

import argparse
import ast
import difflib
import hashlib
from pathlib import Path
import shutil

from .install_xiaozhi import replace_once


EXPECTED = "44ca0310de83e943b48bf1dbf0e0c22715fc7562e387ddd5457383bc061f204b"
MATCHER = '''def _find_best_match(potential_song, music_files):
    """Require a unique exact title; never substitute a similar song."""
    def normalize(value):
        return re.sub(r"[\\W_]+", "", value).casefold()

    requested = normalize(potential_song)
    if not requested:
        return None
    matches = []
    for music_file in music_files:
        stem = os.path.splitext(os.path.basename(music_file))[0]
        names = [stem] + re.split(r"[-_—]", stem)
        if any(normalize(name) == requested for name in names):
            matches.append(music_file)
    return matches[0] if len(matches) == 1 else None
'''


def patch_music(source):
    tree = ast.parse(source)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "_find_best_match")
    lines = source.splitlines(keepends=True)
    source = replace_once(source, "".join(lines[node.lineno - 1:node.end_lineno]), MATCHER)
    source = replace_once(source, "import difflib\n", "")
    source = replace_once(source, "明确指定的时返回音乐的名字",
                          "明确指定时返回歌名，指定歌手时返回歌手-歌名，不得省略歌手或改成random")
    source = replace_once(source, "        await handle_music_command(conn, music_intent)\n",
                          "        if not await handle_music_command(conn, music_intent):\n"
                          "            return ActionResponse(\n"
                          "                action=Action.RESPONSE, result=\"没有唯一匹配的本地歌曲\",\n"
                          "                response=\"本地曲库没有找到您指定的歌曲，或存在多个版本；我不会换成其他歌曲。\"\n"
                          "            )\n")
    source = replace_once(source, "    # 尝试匹配具体歌名\n",
                          "    potential_song = _extract_song_name(clean_text)\n"
                          "    # 尝试匹配具体歌名\n")
    source = replace_once(source, "        potential_song = _extract_song_name(clean_text)\n", "")
    source = replace_once(source, "    # 检查是否是通用播放音乐命令\n",
                          "    if potential_song:\n"
                          "        return False\n"
                          "    # 检查是否是通用播放音乐命令\n")
    ast.parse(source)
    return source


def build_change(path):
    original = path.read_text(encoding="utf-8")
    if hashlib.sha256(original.encode()).hexdigest() != EXPECTED:
        raise ValueError("Refusing unreviewed music plugin; requires exact v0.9.7 source")
    return original, patch_music(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        original, changed = build_change(args.plugin)
        if args.apply:
            backup = args.plugin.with_name(args.plugin.name + ".mia-music-original")
            if backup.exists():
                raise ValueError("Music backup already exists; refusing to overwrite it")
            shutil.copy2(args.plugin, backup)
            try:
                args.plugin.write_text(changed, encoding="utf-8")
            except OSError:
                shutil.copy2(backup, args.plugin)
                raise
        else:
            print("".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                              fromfile=str(args.plugin), tofile=str(args.plugin))), end="")
    except (OSError, ValueError, StopIteration) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
