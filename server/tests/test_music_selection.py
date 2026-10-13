import ast
import os
from pathlib import Path
import re
import tempfile
import time
from types import SimpleNamespace
import unittest

from server.companion.install_music import build_change


class MusicSelectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # CI fetches the pinned upstream file; build_change verifies its exact hash.
        self.source = Path(os.environ["MIA_MUSIC_TEST_SOURCE"])
        _, patched = build_change(self.source)
        tree = ast.parse(patched)
        names = {"_extract_song_name", "_find_best_match", "handle_music_command", "play_music"}
        functions = [node for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
        for node in functions:
            node.decorator_list = []
        self.temp = tempfile.TemporaryDirectory()
        self.played = []
        self.cache = {"music_dir": self.temp.name, "music_files": [], "music_file_names": [],
                      "refresh_time": 60, "scan_time": time.time()}

        async def play(conn, specific_file=None):
            self.played.append(specific_file)

        self.namespace = {"os": os, "re": re, "time": time, "TAG": "music_fixture", "MUSIC_CACHE": self.cache,
                          "initialize_music_handler": lambda conn: self.cache,
                          "play_local_music": play, "ActionResponse": SimpleNamespace,
                          "Action": SimpleNamespace(RESPONSE="response", RECORD="record")}
        exec(compile(ast.Module(body=functions, type_ignores=[]), "patched_music", "exec"), self.namespace)
        self.conn = SimpleNamespace(logger=SimpleNamespace(bind=lambda **kwargs: SimpleNamespace(
            debug=lambda *args: None, info=lambda *args: None, error=lambda *args: None)))

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_song_and_artist_match_but_similar_titles_do_not(self):
        match = self.namespace["_find_best_match"]
        self.assertEqual(match("张学友-偷心", ["张学友-偷心.mp3"]), "张学友-偷心.mp3")
        self.assertEqual(match("偷心", ["张学友-偷心.mp3"]), "张学友-偷心.mp3")
        self.assertIsNone(match("张学友-偷心", ["别的歌手-偷心.mp3"]))
        self.assertIsNone(match("偷心", ["偷心的人.mp3", "一念千年_国风版.mp3"]))

    def test_ambiguous_versions_are_not_chosen_arbitrarily(self):
        self.assertIsNone(self.namespace["_find_best_match"]("偷心", ["偷心.mp3", "偷心.wav"]))

    async def test_missing_requested_song_reports_unavailable_without_random_playback(self):
        self.cache["music_files"] = ["一念千年_国风版.mp3", "廉波老矣，尚能饭否.mp3", "中秋月.mp3"]
        result = await self.namespace["play_music"](self.conn, "偷心")
        self.assertEqual(self.played, [])
        self.assertEqual(result.action, "response")
        self.assertIn("没有找到", result.response)

    async def test_existing_requested_song_plays_only_that_file(self):
        self.cache["music_files"] = ["中秋月.mp3", "张学友-偷心.mp3"]
        result = await self.namespace["play_music"](self.conn, "张学友-偷心")
        self.assertEqual(self.played, ["张学友-偷心.mp3"])
        self.assertEqual(result.action, "record")

    async def test_generic_random_music_still_works(self):
        result = await self.namespace["play_music"](self.conn, "random")
        self.assertEqual(self.played, [None])
        self.assertEqual(result.action, "record")

    async def test_missing_music_directory_does_not_claim_named_song_will_play(self):
        self.cache["music_dir"] = self.temp.name + "/missing"
        result = await self.namespace["play_music"](self.conn, "偷心")
        self.assertEqual(self.played, [])
        self.assertEqual(result.action, "response")

    def test_unreviewed_plugin_is_refused(self):
        changed = Path(self.temp.name) / "play_music.py"
        changed.write_text(self.source.read_text() + "\n# local edit\n")
        with self.assertRaises(ValueError):
            build_change(changed)
