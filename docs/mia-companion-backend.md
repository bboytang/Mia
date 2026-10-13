# Mia 小智服务端扩展部署与回滚

适配 `xiaozhi-esp32-server v0.9.7`，复用现有模型、语音服务、设备认证和绑定。不要启用 Mia 旧网关。

## 适配内容

`server/companion` 安装为小智源码中的 `mia_companion`。安装脚本检查四份上游源码 SHA-256 和唯一锚点，未匹配时拒绝写入；`--check` 只输出补丁。

- manager-api 的已绑定智能体配置追加服务端 `mia_owner=user:<userId>:agent:<agentId>`。
- Python 再验证现有 Bearer 和设备/客户端身份，只有两项证据都有效才开启记忆。不能从请求 owner、昵称或白名单推导身份。
- 在记忆初始化、用户轮次、十轮 checkpoint、断开保存及管理消息处接入模块；短上下文最多20轮。
- 在同一回答的 emoji 标记和 TTS sentence_start 处接入情绪/强度，现有 TTS 移除标记；不开另一模型猜测情绪。
- 修正上游 `re.sub` 字符串替换为 callback，避免真实记忆中的反斜杠被当作替换指令。

SQLite 文件默认是小智根目录 `data/mia-memory.sqlite3`，可通过 `MIA_MEMORY_DB` 指定持久卷路径；不把 DB 放进临时容器层。安装不改现有密钥、令牌、数据库和启动配置。

## 执行顺序

1. 核对运行容器、源码 checkout、实际 tag/改动和现有认证；检查 `mia_owner` 钩子需要的 manager-api 源码。尚未认证或 manager 未更新时，管理返回 unavailable，普通对话继续。
2. 停止发布操作并备份当前配置、源码、manager 构建和记忆数据库；SQLite 热备使用 backup API，不能只复制正在写入的主文件而忽略 WAL。
3. 在待部署源码副本中检查补丁：

```sh
python3 -m server.companion.install_xiaozhi /path/to/xiaozhi-esp32-server --check
```

4. 审阅差异后安装到该副本：

```sh
python3 -m server.companion.install_xiaozhi /path/to/xiaozhi-esp32-server --apply
```

5. 重编 manager-api，构建小智服务镜像；保留既有 compose 配置、网络和密钥挂载，仅加入持久记忆卷/路径。部署前运行 Python 回归、Java 构建，并检查新镜像中包路径。
6. 先用绑定设备测试 hello、无麦克风记忆列表、保存/检索/删除/暂停/性格，再测语音；不以服务器启动成功代替功能验证。

脚本只生成/应用源码补丁，不会自动重启生产服务。现有源码有自定义改动时拒绝自动应用；需先逐项审阅适配，禁止删除用户改动来凑 hash。

## 回滚

停止新进程，恢复四份 `.mia-original` 源码或部署前镜像和 manager 构建，恢复原配置启动。移除本次新增 `mia_companion` 源码目录，不删除持久记忆卷；待修复后仍能读取数据。
脚本重复安装会拒绝覆盖既有包/备份。发生写入失败会尝试恢复源码，备份保留供检查。

## 协议与使用

认证 WebSocket 请求：`{"type":"mia_memory","session_id":"...","request_id":"UUID","action":"list"}`。
动作：list/update/delete/pause/clear/personality/reset_personality；update 需要 id/content，可显式 confirmed；pause 需要 paused。
响应：`{"type":"mia_memory","request_id":"UUID","result":{"memories":[],"paused":false,"personality":{"version":0,"traits":[]}}}`；错误为 error 对象，不回显凭据。
App 管理回复上限1MiB，记录最多200条，每条内容/来源512字；普通协议消息仍64KiB。

自动提炼每十轮或结束时执行；“记住：…”、“请记住……”和“米娅，请记住……”提前触发本轮 checkpoint。“这段别记”暂停本会话提炼；“忘掉关于…的记忆”只在唯一匹配时删除，模糊的“忘掉这件事”先澄清，不能虚称已删除。
敏感候选在 App 中确认后才用于检索/成长。App 删除清理当前数据库与衍生依据；旧服务器备份需管理员另行处理。

## 2026-10-13 实际部署状态

`root@43.143.230.174`，目录 `/opt/xiaozhi-server`。现有设备认证与manager绑定查询保留。原Python源码和Java目标class核对一致；原Java完整构建与生产class一致，补丁再次完整构建后仅替换原JAR目标class，保留其他配置/依赖/迁移文件。

运行镜像 `mia-xiaozhi-server:companion-memory-2d153d4`、`mia-xiaozhi-web:companion-0d9a7cf`。自然记忆口令补丁已部署，完整83项服务端回归通过；真实自然口令在当前连接结束前保存、重连读取及 provider 检索通过，临时记录已删除，原有9条记忆保留。此前已验证管理/删除、三情绪、ASR/VAD/TTS及重启持久化。

维护启动须使用三份文件，避免遗漏Mia覆盖：

```sh
cd /opt/xiaozhi-server
docker compose -f docker-compose_all.yml -f docker-compose.lowmem.yml -f docker-compose.mia.yml up -d --no-deps xiaozhi-esp32-server-web xiaozhi-esp32-server
```

原镜像/源码/JAR/配置/MySQL一致性导出及SQLite热备保存在受保护目录 `/opt/xiaozhi-server/mia-deploy-20261013/backup`。固定原镜像回滚：

```sh
cd /opt/xiaozhi-server
docker compose -f docker-compose_all.yml -f docker-compose.lowmem.yml -f mia-deploy-20261013/rollback.yml up -d --no-deps xiaozhi-esp32-server-web xiaozhi-esp32-server
```

回滚不删除SQLite或绑定；重新部署使用上方Mia覆盖。沿用原模型供应商，长期提炼准确率、成本和成长质量仍需观察，后台/锁屏与系统口令需iPhone真机验收。

## 自然记忆补丁与音色选择（2026-10-13）

补丁部署目录 `/opt/xiaozhi-server/mia-memory-natural-20261013-2d153d4`，`backup` 保存部署前 Compose、适配器和 SQLite backup API 热备。新镜像以 `companion-40c715d` 为父镜像，仅替换适配器；管理后台、MySQL、Redis及其他Python源码不变。回滚这次记忆补丁时，使用该目录 `backup/docker-compose.mia.yml` 作为第三份 Compose 覆盖，只重建 `xiaozhi-esp32-server`，不恢复旧SQLite覆盖现有记忆。

绑定设备的服务端配置仍为 `Memory_nomem`。这是小智原生记忆提供者的选择；Mia根据服务端认证归属另行初始化自己的提供者，并覆盖原生提供者。因此使用Mia记忆无需将截图中的“记忆模式”改为本地短期记忆、Mem0AI或PowerMem。Mia App的“设置→记忆与成长”管理记录、敏感确认和暂停状态。

当前测试智能体仍选用 `TTS_HuoshanDoubleStreamTTS` / Vivi，App未写死音色。这个测试型号资源是 `seed-tts-2.0`，但其27条音色多数仍为旧版编码。自由选择时，应在绑定Mia设备的智能体配置里将“语音合成(TTS)”切换为“豆包语音合成2.0(流式)”（`TTS_HSDSTTS_V2`），再选择对话语言和“声音音色(Voice)”，保存配置，然后在Mia结束并重新开始对话。

后台已有该2.0型号的40条音色。其appid/access_token原为占位内容，本次仅复用现有有效型号的两项凭据，保留其他参数及当前智能体选择；原配置备份为 `backup/tts-v2-original-config.json`（权限600），已按上游缓存规则删除该型号的配置/名称缓存。无需新密钥或重装App。

真实2.0合成验证：湾湾小何返回50个Opus包/7845字节；阳光青年返回46个Opus包/7199字节。其他38种未逐一合成，也未验收iPhone播放。2.0资源应使用2.0音色，见[火山双向流式接口](https://docs.volcengine.com/docs/DoubaoVoice/WebSocketBidirectionalStreaming-V3?lang=zh)。缺少所需音色时，可在“模型配置→语音合成→对应型号的音色管理”添加官方兼容编码，再回智能体选择；只改模型默认speaker不会覆盖智能体已选的private_voice。

## 指定歌曲缺失时不再换歌（2026-10-14）

用户请求张学友《偷心》，生产ASR与工具日志显示识别正确，但本地曲库仅三首歌且没有《偷心》。v0.9.7插件会在匹配失败时随机播放；本次修复为仅唯一准确匹配才播放，指定歌手保留歌手-歌名，缺歌/歧义明确返回不可用，明确随机播放仍保留。未接入新音乐源或下载歌曲，不能声称已经能播放《偷心》。

源码补丁入口为 `python -m server.companion.install_music /path/to/play_music.py --check` 或 `--apply`；严格校验原始v0.9.7的SHA256并保留原文件，不覆盖自定义插件。GitHub [服务端回归](https://github.com/bboytang/Mia/actions/runs/38480040295)的90项测试通过，产物为已打补丁的完整插件。

用户在部署方案明确说明后回复“继续”，已备份并将该GitHub产物只读挂载到语音容器，保留原镜像 `mia-xiaozhi-server:companion-memory-2d153d4`。插件路径 `/opt/xiaozhi-server/mia-music-6f78f48/play_music.py`，SHA256 `6fe21451135ceb3cad6131a99e60a9cb1eee042bab4b3006cab954ee62b4ead5`；`docker-compose.mia.yml`增加单文件挂载，原三份Compose启动命令继续适用。只重建Python语音容器，web/MySQL/Redis不重启，数据卷与记忆保留；容器运行、挂载/校验值和无启动错误已核对，用户实际音乐请求仍待验。

备份在同目录 `backup/`，包含原插件和原 `docker-compose.mia.yml`。回滚时恢复后者，再用原三份Compose仅重建语音服务；移除挂载后恢复原镜像插件，无需覆盖记忆数据库。所有自动化回归和产物生成在GitHub进行，本次服务器未进行镜像构建。
