import json
import os
from pathlib import Path
import tempfile
import unittest

from server.companion import MemoryError, MemoryStore, parse_extraction


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.sqlite3"
        self.now = [1_800_000_000]
        self.store = MemoryStore(self.path, clock=lambda: self.now[0])
        self.counter = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_management_capabilities_are_additive_to_legacy_snapshot(self):
        result = self.store.handle('alice', {'action': 'list'})
        self.assertEqual(result['memories'], [])
        self.assertFalse(result['paused'])
        self.assertEqual(result['personality']['traits'], [])
        self.assertEqual(result['management']['version'], 1)
        self.assertIn('emotion_consent', result['management']['actions'])
        self.assertIn('event_delete', result['management']['actions'])
        self.assertEqual(self.store.handle('alice', {'action': 'emotion_status'})['trend'], {'status': 'disabled'})

    def remember(self, content, owner="alice", session="one", source=None, sensitive=False, category="preference", **extra):
        self.counter += 1
        result = self.store.apply_extraction(owner, session, self.store.snapshot(owner)["revision"],
            [source or content], {"memories": [{"category": category, "content": content,
            "source_index": 0, "sensitive": sensitive, **extra}]}, str(self.counter))
        return result["memories"][0] if result["memories"] else None

    def trait(self, ids, name="坦率", checkpoint="trait", revision=None):
        return self.store.apply_extraction("alice", "growth", revision if revision is not None else
            self.store.snapshot("alice")["revision"], ["今天的聊天反馈"], {"memories": [],
            "trait": {"name": name, "description": "表达更直接，保留自己的判断", "evidence_ids": ids}}, checkpoint)

    def test_persistence_permissions_and_owner_isolation(self):
        first = self.remember("我喜欢蓝色")
        self.remember("我喜欢红色", owner="bob")
        self.store.close()
        self.store = MemoryStore(self.path)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        self.assertEqual([r["id"] for r in self.store.list_memories("alice")], [first])
        self.assertEqual(self.store.retrieve("bob", "蓝色")[0]["content"], "我喜欢红色")
        with self.assertRaises(MemoryError):
            self.store.delete_memory("bob", first)
        self.assertEqual(self.store.list_memories("alice")[0]["id"], first)
        with self.assertRaises(MemoryError):
            self.store.edit_memory("bob", first, "别人不能修改")
        self.store.clear("bob")
        self.assertEqual(len(self.store.list_memories("alice")), 1)

    def test_chinese_and_english_retrieval_bounded_to_eight(self):
        blue = self.remember("我喜欢蓝色")
        project = self.remember("正在准备毕业项目")
        self.remember("I enjoy astronomy")
        for i in range(12):
            self.remember(f"日常偏好第{i}项")
        self.assertEqual(self.store.retrieve("alice", "蓝色")[0]["id"], blue)
        self.assertEqual(self.store.retrieve("alice", "毕业项目进展")[0]["id"], project)
        self.assertEqual(self.store.retrieve("alice", "ASTRONOMY")[0]["content"], "I enjoy astronomy")
        self.assertEqual(len(self.store.retrieve("alice", "日常偏好")), 8)
        for query, limit in [("a" * 4097, 8), ("项目", 9), ("项目", True), (None, 8)]:
            with self.assertRaises(MemoryError):
                self.store.retrieve("alice", query, limit)

    def test_sensitive_candidates_require_explicit_confirmation(self):
        memory = self.remember("正在治疗焦虑症", sensitive=False)
        self.assertFalse(self.store.list_memories("alice")[0]["confirmed"])
        self.assertEqual(self.store.retrieve("alice", "治疗"), [])
        self.store.edit_memory("alice", memory, "正在治疗焦虑症", confirmed=True)
        self.assertEqual(len(self.store.retrieve("alice", "治疗")), 1)
        self.store.edit_memory("alice", memory, "每月工资两万元")
        self.assertEqual(self.store.retrieve("alice", "工资"), [])
        pending = self.remember("这是一件私密的经历", sensitive=True)
        self.assertNotIn(pending, [r["id"] for r in self.store.retrieve("alice", "经历")])

    def test_credentials_never_enter_memories_sources_or_traits(self):
        for secret in ["我的密码是abc123", "验证码是123456", "api_key: example-value",
                       "授权码是example", "私有凭据是example", "private_credential: example",
                       "authorization_code: example", "Mia-Private-Credential: example",
                       "Bearer testing", "sk-proj-example", "PRIVATE secret is abc", "ＰＡＳＳＷＯＲＤ：123456"]:
            with self.subTest(secret=secret), self.assertRaises(MemoryError):
                self.remember(secret)
        self.assertIsNone(self.remember("喜欢直接回答", source="喜欢直接回答，密码是abc123"))
        with self.assertRaises(MemoryError):
            parse_extraction({"trait": {"name": "记得密码", "description": "不要保存", "evidence_ids": ["x"]}})
        self.assertEqual(self.store.list_memories("alice"), [])

    def test_fenced_json_saves_memory_without_unsupported_trait(self):
        data = {"memories": [{"category": "preference", "content": "喜欢蓝色", "source_index": 0}],
                "trait": {"name": "审美偏好", "description": "喜欢蓝色", "evidence_ids": []}}
        result = self.store.apply_extraction("alice", "one", 0, ["我喜欢蓝色"],
            "```json\n" + json.dumps(data) + "\n```", "fenced")
        self.assertEqual(len(result["memories"]), 1)
        self.assertFalse(result["trait_updated"])
        self.assertEqual(self.store.personality("alice"), {"version": 0, "traits": []})
        for wrapped in ["prose\n```json\n{}\n```", "```json\n{}\n```\nprose"]:
            with self.assertRaises(MemoryError):
                parse_extraction(wrapped)

    def test_extraction_validation_is_atomic_and_bounded(self):
        valid = {"category": "fact", "content": "喜欢天空", "source_index": 0}
        invalid = [None, "not JSON", "x" * 24001, [], {"memories": {}},
                   {"memories": [valid] * 17}, {"memories": [{**valid, "category": []}]},
                   {"memories": [{**valid, "content": "x" * 513}]},
                   {"memories": [{**valid, "source_index": True}]},
                   {"memories": [{**valid, "sensitive": "false"}]},
                   {"trait": {"name": "a", "description": "b", "evidence_ids": ["x"] * 17}}]
        for payload in invalid:
            with self.subTest(payload=repr(payload)[:100]), self.assertRaises(MemoryError):
                parse_extraction(payload)
        self.assertEqual(parse_extraction(json.dumps({"memories": [valid]}))["memories"][0]["content"], "喜欢天空")
        for payload in [{"memories": [valid, {**valid, "source_index": 19}]},
                        {"memories": [valid, {**valid, "category": "unknown"}]}]:
            with self.assertRaises(MemoryError):
                self.store.apply_extraction("alice", "one", 0, ["喜欢天空"], payload, "bad")
        self.assertEqual(self.store.list_memories("alice"), [])

    def test_destructive_mutations_invalidate_in_flight_snapshots(self):
        for operation in ["delete", "edit", "clear", "pause", "reset"]:
            with self.subTest(operation=operation):
                self.store.clear("alice")
                memory = self.remember("曾经喜欢蓝色")
                revision = self.store.snapshot("alice")["revision"]
                if operation == "delete":
                    self.store.delete_memory("alice", memory)
                elif operation == "edit":
                    self.store.edit_memory("alice", memory, "现在喜欢绿色")
                elif operation == "clear":
                    self.store.clear("alice")
                elif operation == "pause":
                    self.store.set_paused("alice", True)
                    self.store.set_paused("alice", False)
                else:
                    self.store.reset_personality("alice")
                result = self.store.apply_extraction("alice", "old", revision, ["曾经喜欢蓝色"],
                    {"memories": [{"category": "preference", "content": "曾经喜欢蓝色", "source_index": 0}]}, "old")
                self.assertFalse(result["applied"])

    def test_generation_guard_works_across_two_connections(self):
        memory = self.remember("准备重要项目")
        stale = self.store.snapshot("alice")["revision"]
        other = MemoryStore(self.path)
        try:
            other.delete_memory("alice", memory)
            self.assertFalse(self.trait([memory], revision=stale)["applied"])
            self.assertEqual(self.store.list_memories("alice"), [])
        finally:
            other.close()

    def test_personality_needs_three_distinct_sessions_and_sources(self):
        memory = self.remember("喜欢直接的反馈", session="one", source="希望你直接指出我的问题")
        self.remember("喜欢直接的反馈", session="one", source="这次可以更坦率")
        self.assertFalse(self.trait([memory], checkpoint="only-one")["trait_updated"])
        self.remember("喜欢直接的反馈", session="two", source="希望你直接指出我的问题")
        self.remember("喜欢直接的反馈", session="three", source="希望你直接指出我的问题")
        self.assertFalse(self.trait([memory], checkpoint="repeated-source")["trait_updated"])
        self.remember("喜欢直接的反馈", session="three", source="不同意见也可以直接告诉我")
        self.assertEqual(self.store.list_memories("alice")[0]["evidence_session_count"], 3)
        self.assertEqual(self.store.list_memories("alice")[0]["evidence_source_count"], 3)
        result = self.trait([memory], checkpoint="enough")
        self.assertTrue(result["trait_updated"])
        self.assertEqual(self.store.personality("alice")["version"], 1)
        self.assertEqual(self.store.personality("alice")["traits"][0]["evidence_ids"], [memory])
        self.assertFalse(self.trait([memory], name="新特征", checkpoint="enough")["applied"])
        self.assertFalse(self.trait([memory], checkpoint="unchanged")["trait_updated"])
        self.store.delete_memory("alice", memory)
        self.assertEqual(self.store.personality("alice")["traits"], [])
        self.assertEqual(self.store.personality("alice")["version"], 2)

    def test_pending_or_foreign_evidence_cannot_create_trait(self):
        foreign = self.remember("喜欢蓝色", owner="bob")
        pending = self.remember("健康问题", sensitive=True)
        self.assertFalse(self.trait([foreign, pending])["trait_updated"])

    def test_three_independent_sources_must_belong_to_three_sessions(self):
        memory = self.remember("喜欢直接反馈", session="one", source="第一次希望你直接指出问题")
        self.remember("喜欢直接反馈", session="one", source="第二次强调要坦率")
        self.remember("喜欢直接反馈", session="one", source="第三次接受不同意见")
        for session in ["two", "three"]:
            self.remember("喜欢直接反馈", session=session, source="第一次希望你直接指出问题")
        self.assertFalse(self.trait([memory])["trait_updated"])

    def test_correction_removes_old_sources_and_blocks_stale_tasks(self):
        memory = self.remember("喜欢蓝色")
        old = self.store.snapshot("alice")["revision"]
        revised = self.remember("其实现在喜欢绿色", replaces_id=memory, source="纠正一下，我喜欢绿色")
        self.assertEqual(revised, memory)
        self.assertEqual(len(self.store.list_memories("alice")), 1)
        self.assertEqual(self.store.list_memories("alice")[0]["source"], "纠正一下，我喜欢绿色")
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM sources WHERE memory_id=?", (memory,)).fetchone()[0], 1)
        self.assertFalse(self.trait([memory], revision=old)["applied"])

    def test_management_controls_and_reset_preserve_memories(self):
        memory = self.remember("喜欢天文")
        response = self.store.handle("alice", {"action": "pause", "paused": True})
        self.assertTrue(response["paused"])
        self.assertIsNone(self.remember("不应该保存"))
        self.store.handle("alice", {"action": "pause", "paused": False})
        response = self.store.handle("alice", {"action": "update", "id": memory, "content": "喜欢星空"})
        self.assertEqual(response["memories"][0]["content"], "喜欢星空")
        self.store.handle("alice", {"action": "reset_personality"})
        self.assertEqual(len(self.store.handle("alice", {"action": "list"})["memories"]), 1)
        self.store.handle("alice", {"action": "clear"})
        self.assertEqual(self.store.handle("alice", {"action": "list"})["memories"], [])
        for request in [[], {"action": []}, {"action": "unknown"}, {"action": "pause", "paused": 1}]:
            with self.assertRaises(MemoryError):
                self.store.handle("alice", request)

    def test_sensitive_new_source_requires_reconfirmation(self):
        memory = self.remember("喜欢直接反馈")
        self.remember("喜欢直接反馈", session="two", source="因为正在治疗焦虑症，所以请直接反馈")
        self.assertEqual(self.store.list_memories("alice")[0]["id"], memory)
        self.assertFalse(self.store.list_memories("alice")[0]["confirmed"])
        self.assertEqual(self.store.retrieve("alice", "反馈"), [])


if __name__ == "__main__":
    unittest.main()
