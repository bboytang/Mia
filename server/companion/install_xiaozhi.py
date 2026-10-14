"""Review/apply a small, preimage-checked patch to an exact v0.9.7 checkout."""

import argparse
import ast
import difflib
import hashlib
from pathlib import Path
import shutil


PYTHON = "main/xiaozhi-server/"
JAVA = "main/manager-api/src/main/java/xiaozhi/modules/config/service/impl/ConfigServiceImpl.java"
EXPECTED = {
    PYTHON + "core/connection.py": "a1d6694197a2422d777a85cb55becb63b66278c1d23588782f39dc98a8954386",
    PYTHON + "core/handle/sendAudioHandle.py": "9b9dba36e4f110017596f975503d893d1a134071bf953ce9021020b8d0436c6e",
    PYTHON + "core/utils/dialogue.py": "a4f7af45edd5f1e60a119eb698daba56047fb6c57dfe5c4bfcadbf28234a6602",
    JAVA: "9f6a782d2c25fc015d4ffc6a799085b0439884bdadc4d0a7f47eeebd9256aac1",
}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("Upstream hook preimage is missing or ambiguous")
    return text.replace(before, after, 1)


def patch_connection(text):
    text = replace_once(text, "from core.utils.dialogue import Message, Dialogue\n",
                        "from core.utils.dialogue import Message, Dialogue\nfrom mia_companion import xiaozhi_adapter as mia\n"
                        "from mia_companion import authorization as mia_auth\n")
    text = replace_once(text, 'f"{self.client_ip} conn - Headers: {self.headers}"',
                        'f"{self.client_ip} conn - Header names: {sorted(self.headers)}"')
    text = replace_once(text, 'from config.config_loader import get_private_config_from_api\n', '')
    text = replace_once(text, '            private_config = await get_private_config_from_api(\n'
                        '                self.config,\n                self.headers.get("device-id"),\n'
                        '                self.headers.get("client-id", self.headers.get("device-id")),\n            )',
                        '            private_config = await mia_auth.load_private_config(self)')
    text = replace_once(text, '            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))\n',
                        '            mia.attach_private_config(self, private_config)\n'
                        '            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))\n')
    text = replace_once(text, '        except DeviceNotFoundException as e:\n',
                        '        except mia_auth.PrivateAuthorizationRequired:\n'
                        '            self.need_bind = False\n'
                        '            self._mia_authorization_required = True\n'
                        '            self.bind_completed_event.set()\n'
                        '            self.report_asr_enable = False\n'
                        '            self.report_tts_enable = False\n'
                        '            await mia_auth.prompt_authorization(self)\n'
                        '            return\n'
                        '        except DeviceNotFoundException as e:\n')
    text = replace_once(text, '            # 在线程池中初始化组件\n',
                        '            if getattr(self, "_mia_authorization_required", False):\n                return\n'
                        '            # 在线程池中初始化组件\n')
    text = replace_once(text, '        # 已经获取到真实状态，检查是否需要绑定\n',
                        '        if getattr(self, "_mia_authorization_required", False):\n'
                        '            await mia_auth.route_required(self, message)\n            return\n\n'
                        '        # 已经获取到真实状态，检查是否需要绑定\n')
    text = replace_once(text, '                # 超时仍未获取到真实状态，丢弃消息\n'
                        '                await self._discard_message_with_bind_prompt()\n                return',
                        '                # 身份结果未就绪时不误报为需要重新绑定。\n                return')
    text = replace_once(text, 'await asyncio.wait_for(self.bind_completed_event.wait(), timeout=1)',
                        'await asyncio.wait_for(self.bind_completed_event.wait(), timeout=4)')
    text = replace_once(text, "    def _initialize_memory(self):\n        if self.memory is None:\n",
                        "    def _initialize_memory(self):\n        if mia.initialize_memory(self):\n            return\n        if self.memory is None:\n")
    text = replace_once(text, "            self._init_prompt_enhancement()\n",
                        "            self._init_prompt_enhancement()\n            mia.apply_persona_prompt(self)\n")
    text = replace_once(text, "        if isinstance(message, str):\n            await handleTextMessage(self, message)\n",
                        "        if isinstance(message, str):\n            if await mia.handle_message(self, message):\n                return\n            await handleTextMessage(self, message)\n")
    text = replace_once(text, '            self.dialogue.put(Message(role="user", content=query))\n',
                        '            mia.begin_turn(self, query)\n            self.dialogue.put(Message(role="user", content=query))\n')
    text = replace_once(text, "                if emotion_flag and content is not None and content.strip():\n",
                        "                if emotion_flag and content is not None and content.strip():\n                    mia.remember_emotion(self, content)\n")
    text = replace_once(text, "        if depth == 0:\n            self.tts.tts_text_queue.put(\n",
                        "        if depth == 0:\n            mia.checkpoint(self)\n            self.tts.tts_text_queue.put(\n")
    text = replace_once(text, '    def chat(self, query, depth=0):\n',
                        '    def chat(self, query, depth=0):\n'
                        '        if not mia_auth.allow_generation(self):\n            return\n')
    text = replace_once(text, '                        self.func_handler.handle_llm_function_call(\n'
                        '                            self, tool_call_data\n                        ),',
                        '                        mia_auth.execute_tool(self, tool_call_data),')
    return text


def patch_tts(text):
    text = replace_once(text, "from core.utils import textUtils\n",
                        "from core.utils import textUtils\nfrom mia_companion import xiaozhi_adapter as mia\n"
                        "from mia_companion import authorization as mia_auth\n")
    text = replace_once(text, '    packet_index = flow_control.get("packet_count", 0)\n',
                        '    if not await mia_auth.allow_output(conn):\n        return\n'
                        '    packet_index = flow_control.get("packet_count", 0)\n')
    text = replace_once(text, '    message = {"type": "tts", "state": state, "session_id": conn.session_id}\n',
                        '    if not await mia_auth.allow_output(conn):\n        return\n'
                        '    message = {"type": "tts", "state": state, "session_id": conn.session_id}\n')
    return replace_once(text, '    if text is not None:\n        message["text"] = textUtils.check_emoji(text)\n',
                        '    if text is not None:\n        message["text"] = textUtils.check_emoji(text)\n'
                        '    if state == "sentence_start":\n        message.update(mia.tts_emotion(conn, text))\n')


def patch_dialogue(text):
    text = replace_once(text, "from datetime import datetime\n",
                        "from datetime import datetime\nfrom mia_companion.xiaozhi_adapter import bounded_history\n")
    text = replace_once(text, '                    f"<memory>\\n{memory_str}\\n</memory>",\n',
                        '                    lambda _: f"<memory>\\n{memory_str}\\n</memory>",\n')
    return replace_once(text, "        actual_messages = [m for m in non_system_messages if not m.is_temporary]\n",
                        "        actual_messages = [m for m in non_system_messages if not m.is_temporary]\n"
                        "        if memory_str and memory_str.startswith('{\"mia_context\":'):\n"
                        "            actual_messages = bounded_history(actual_messages)\n")


def patch_manager(text):
    return replace_once(text, '        result.put("chat_history_conf", chatHistoryConf);\n',
                        '        result.put("chat_history_conf", chatHistoryConf);\n'
                        '        result.put("mia_owner", "user:" + agent.getUserId() + ":agent:" + agent.getId());\n')


PATCHERS = dict(zip(EXPECTED, [patch_connection, patch_tts, patch_dialogue, patch_manager]))


def build_changes(root):
    changes = {}
    for relative, digest in EXPECTED.items():
        path = root / relative
        original = path.read_text(encoding="utf-8")
        normalized = original.rstrip("\n") + "\n"
        if hashlib.sha256(normalized.encode()).hexdigest() != digest:
            raise ValueError(f"Refusing unreviewed source: {relative}; requires clean xiaozhi v0.9.7")
        changed = PATCHERS[relative](original)
        if relative.endswith(".py"):
            ast.parse(changed, filename=relative)
        changes[relative] = (original, changed)
    return changes


def install(root, changes):
    destination = root / PYTHON / "mia_companion"
    if destination.exists():
        raise ValueError("mia_companion already exists; review and restore the previous installation first")
    backups = [root / (relative + ".mia-original") for relative in changes]
    if any(path.exists() for path in backups):
        raise ValueError("Original backups already exist; refusing to overwrite them")
    for relative in changes:
        shutil.copy2(root / relative, root / (relative + ".mia-original"))
    destination.mkdir(mode=0o700)
    try:
        for name in ["__init__.py", "memory.py", "xiaozhi_adapter.py", "authorization.py"]:
            shutil.copy2(Path(__file__).parent / name, destination / name)
        for relative, (_, changed) in changes.items():
            (root / relative).write_text(changed, encoding="utf-8")
    except OSError:
        for relative in changes:
            shutil.copy2(root / (relative + ".mia-original"), root / relative)
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="Full xiaozhi-esp32-server v0.9.7 repository")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate and print the proposed diff; write nothing")
    mode.add_argument("--apply", action="store_true", help="Copy adapter, back up originals and apply the checked patch")
    args = parser.parse_args()
    try:
        changes = build_changes(args.upstream)
        if args.apply:
            install(args.upstream, changes)
            print("Installed Mia companion hooks. Rebuild/restart manager-api and xiaozhi-server; existing databases were not changed.")
        else:
            for relative, (original, changed) in changes.items():
                print("".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                               fromfile="a/" + relative, tofile="b/" + relative)), end="")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
