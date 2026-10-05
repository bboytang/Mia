# Mia 本地协议测试服务

这是小智 WebSocket 版本 1 的联调夹具，不提供语音识别、AI 对话或真正的人声合成。收到 `listen/stop` 后，它返回固定的 Mia 文本与 1.2 秒 Opus 测试音，用来检查客户端连接、二进制音频解码和字幕推进。

Ubuntu 上运行：

```bash
sudo apt-get install -y libopus0 python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r server/requirements.txt
python -m server.mock_xiaozhi
```

默认只监听 `127.0.0.1:8765`。iPhone 端要求 `wss://`，所以远程联调还需在服务器上使用带 TLS 证书的反向代理转发到这个本地端口。可设置 `MIA_MOCK_TOKEN` 要求 `Authorization: Bearer <token>`；令牌只放在服务器环境中。不要把这个固定答复服务当作公开生产服务。

本地测试：`python -m unittest discover -s server/tests -v`。

## 正式云语音网关

`server.xiaozhi_gateway` 接收 16 kHz 单声道 Opus，经火山豆包流式 ASR 2.0、方舟 `doubao-seed-2-1-lite-260915` 和 Seed-TTS 2.0 双向 WebSocket，发送 24 kHz Opus。iOS 只收到 Mia 的回答字幕，不收到用户识别文本。百炼 Provider 暂保留，供真实迁移验证前回滚。

在 Ubuntu 上安装上述 Python 依赖后，使用环境变量启动：

```bash
export MIA_GATEWAY_TOKEN='自行生成的长随机令牌'
export MIA_PROVIDER=volcengine
export VOLC_ARK_API_KEY='仅在服务器上设置的方舟 Key'
export VOLC_VOICE_API_KEY='仅在服务器上设置的豆包语音 Key'
export MIA_CHAT_MODEL=doubao-seed-2-1-lite-260915
export MIA_ASR_RESOURCE_ID=volc.seedasr.sauc.duration
export MIA_TTS_RESOURCE_ID=seed-tts-2.0
python -m server.xiaozhi_gateway
```

方舟 Key 仅用于 LLM；同一把豆包语音 Key 用于 ASR 与 TTS。默认模型和资源 ID 如上，LLM 第一阶段为非流式。回滚时可设置 `MIA_PROVIDER=bailian`，并保留旧 `DASHSCOPE_API_KEY` 与 `MIA_BAILIAN_REGION=cn-beijing`；回滚后将 `MIA_CHAT_MODEL` 改回 `qwen-plus` 或移除。管理员高级维护模式的访问令牌填 `MIA_GATEWAY_TOKEN`，日常使用改为账号注册/登录；地址填 `wss://8kraw.cloud/xiaozhi/v1/`，不能填本机 `ws://` 地址。

部署模板位于 `server/deploy/`：代码安装到 `/opt/mia`，以 `mia` 账户和独立虚拟环境运行；`/etc/mia/gateway.env` 仅 root 可读。Caddy 把 `8kraw.cloud/xiaozhi/v1/` 转发到本机 `127.0.0.1:8765`。中国内地 VPS 地址是 `43.143.230.174`。不要把密钥或令牌写进仓库或聊天。

在 VPS 上先部署代码和空白 Key 字段：

```bash
ssh ubuntu@43.143.230.174
# 仓库已位于 /home/ubuntu/Mia；更新代码后执行：
sudo bash /home/ubuntu/Mia/server/deploy/install-ubuntu.sh
```

脚本保留已有 `/etc/mia/gateway.env` 和网关令牌，只补齐缺失的火山配置字段；新安装才生成令牌。脚本不读取 Key，也不重启现有网关。代码部署及检查结束后，由服务器管理员通过 `sudoedit /etc/mia/gateway.env` 填入 `VOLC_ARK_API_KEY`、`VOLC_VOICE_API_KEY`，不要给值加引号或空格。确认文件权限 `0600`，再执行 `sudo systemctl restart mia-gateway`。此前旧进程仍使用旧配置；重启后才切至火山。需要回滚时设置 `MIA_PROVIDER=bailian` 并重启，保留旧百炼实现直到真实验证成功。

Caddy 站点沿用现有 `/etc/caddy/Caddyfile`；新安装可加入 `server/deploy/Caddyfile.example`。检查：

```bash
caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status mia-gateway --no-pager
curl -I https://8kraw.cloud/
cd /home/ubuntu/Mia && /opt/mia/.venv/bin/python server/deploy/check_wss.py
```

握手脚本只验证 TLS、令牌及小智协议，不会调用云 API。部署后需另行进行一次真实语音全链路验证；在填入两把 Key 前，不能将新网关视为已投入运行。更新代码重复运行安装脚本不会轮换令牌。

火山三条 API 曾在真实中国 VPS 上分别验证成功：方舟返回 HTTP 200 和 `OK`；Seed-TTS 2.0 双向 WebSocket 生成 171592 字节 24 kHz PCM；ASR 2.0 将转换后的 16 kHz PCM 识别为“你好，我是 Mia。这是实时语音测试。”用户随后在 VPS 设置两把 Key 并重启；新网关已用这段合成语音由 **VPS 自身**经公网域名完成真实全链路回合，返回 Mia 字幕与 91 帧可解码 Opus，错误令牌被拒绝。2026-10-04 iPhone 在 5G/Wi‑Fi 均报 TLS 连接错误，独立外部环境的 TLS 也在 ClientHello 后被重置；用户确认域名尚未完成中国内地 ICP 备案或腾讯云接入。需先在腾讯云核对拦截与备案状态，再验证外部 HTTPS/WSS 和真机语音。自动化测试使用模拟服务，不会调用真实 API。

## 用户名与密码账号

账号 HTTP 与语音网关共用进程，但只监听 `127.0.0.1:8766`；安装脚本默认开启 `MIA_ACCOUNTS_ENABLED=1`。Caddy 在原站点新增 `/api/auth/*` 路由并覆盖 `X-Mia-Client-IP` 为实际客户端 IP，原 `/xiaozhi/v1/*` 不变。不要把 8765/8766 开放到公网。

| 配置 | 默认值 |
| --- | --- |
| `MIA_ACCOUNTS_ENABLED` | `1`（安装器默认；旧环境未设置仍为 `0`） |
| `MIA_ACCOUNT_DB` | `/var/lib/mia/accounts.sqlite3` |
| `MIA_MAX_ACCOUNTS` | `100` |
| `MIA_DAILY_ROUNDS` | `30` / 账号 / UTC 日 |
| `MIA_MAX_CONCURRENT_ROUNDS` | `2`，包含维护访问 |

数据库归 `mia` 所有，systemd `StateDirectory=mia`、目录 `0700`、`UMask=0077`；环境文件仍为 root `0600`。密码只保存独立盐的 scrypt 摘要，会话只保存 SHA-256；30 天有效、每账号最多 5 个会话。每次连接及新云回合前检查会话，撤销后现有连接也不能开始下一回合。空录音或全局忙不扣次数，已经开始的失败/打断会计入。注册上限、每分钟 IP/用户名限制和两个实际哈希线程限制用于控制资源与费用。

接口为 `POST /api/auth/register`（201）、`login`（200）、`logout`（204，重复撤销仍成功），响应 `Cache-Control: no-store`，JSON 上限 4 KiB。注册/登录成功仅向调用者返回其会话；不要记录请求体或 Authorization。用户名为 3–32 个字母、数字、汉字或下划线，NFKC/casefold 后唯一；密码 15–128 个字符，支持且保留空格。

### 管理与自测

在 VPS 的私有终端执行本机密码重置，隐藏输入两次新密码，同时撤销该账号全部会话：

```bash
cd /opt/mia
sudo -u mia /opt/mia/.venv/bin/python -m server.account_admin 用户名
```

账号部署自测仅生成内存中的临时凭据，验证注册、登录、WebSocket 握手、退出、错误/撤销凭据与现有连接的新回合拒绝；不调用云 API。结束时只删除自己创建的临时账号，不输出凭据：

```bash
cd /opt/mia
sudo -u mia /opt/mia/.venv/bin/python -m server.deploy.check_accounts
sudo -u mia /opt/mia/.venv/bin/python -m server.deploy.check_accounts \
  --origin https://8kraw.cloud --endpoint wss://8kraw.cloud/xiaozhi/v1/
```

重复运行安装器保留已有配置、Key、维护令牌和数据库，只补缺失字段。发布前备份代码、systemd/Caddy/环境文件，数据库使用 SQLite backup API（不能在运行中仅复制主文件）。备份目录不得公开或提交 Git。回滚保留账号库，关闭 `MIA_ACCOUNTS_ENABLED=0`、恢复之前服务/代码/Caddy 配置并重启即可使用维护令牌；账号登录将在回滚期间不可用。切勿删除账号库以回滚。

VPS 本机成功不能代替公网或 iPhone 验收：当前域名备案审核期间，仍需独立外部 HTTPS/WSS 和实际注册/语音反馈。

### 当前账号部署验收（2026-10-05）

运行源码 `abe1ae4` 已在 `43.143.230.174` 启用，49 项服务端测试、pip check、Caddy 验证、本机 HTTP 与域名 HTTPS/WSS 的临时账号自测全部通过，测试账号已清理。8765/8766 均只监听 loopback；目录/数据库/环境文件权限分别为 mia `0700`、mia `0600`、root `0600`。旧配置内容逐字保留，现有 Key 和维护令牌没有改变。

旧代码/配置备份：`/var/backups/mia/before-accounts-abe1ae4c4f0f/`，root `0700`；部署前无账号数据库，回滚时必须保留现有账号库。运行提交标记为 `/opt/mia/DEPLOYED_COMMIT`；远端源码是归档快照，不是 Git checkout。外部 HTTPS 仍被重置，待备案恢复后进行真正外部注册和 iPhone 验收。
