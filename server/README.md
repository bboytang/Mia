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

`server.xiaozhi_gateway` 接收 16 kHz 单声道 Opus，调用阿里云百炼的 `qwen3-asr-flash`、`qwen-plus`、`qwen3-tts-flash`，再发送 24 kHz Opus。iOS 只收到 Mia 的 TTS 文本，不收到用户 STT 文本。百炼 API 会产生费用。

在 Ubuntu 上安装上述 Python 依赖后，使用环境变量启动：

```bash
export MIA_GATEWAY_TOKEN='自行生成的长随机令牌'
export DASHSCOPE_API_KEY='只存放在服务器上的百炼 API Key'
export MIA_BAILIAN_REGION='cn-beijing'  # 新加坡 Key 则改为 ap-southeast-1
python -m server.xiaozhi_gateway
```

`MIA_BAILIAN_REGION` 必须与 API Key 的地域相同，目前支持北京和新加坡；美国地域不支持此处采用的 OpenAI 兼容 ASR 接口。可选变量：`MIA_ASR_MODEL`、`MIA_CHAT_MODEL`、`MIA_TTS_MODEL`、`MIA_TTS_VOICE`。客户端设置中的访问令牌填 `MIA_GATEWAY_TOKEN`，服务端地址填 `wss://8kraw.cloud/xiaozhi/v1/`。**不能直接把本机监听的 `ws://` 地址填进 iPhone 客户端。**

部署模板位于 `server/deploy/`：将代码放在 `/opt/mia`，建立非 root 用户 `mia` 和虚拟环境；把 `gateway.env` 放到 `/etc/mia/` 并限制权限；用 systemd 启动网关，再让 Caddy 将 `8kraw.cloud` 上的 `/xiaozhi/v1/` 转发至本地 `127.0.0.1:8765`。域名已解析至 `199.102.217.22`；还需确认 VPS 放行 80/443 端口以申请 TLS 证书。不要把密钥或令牌写进仓库。

北京地域的 VPS 快速安装（在你自己的终端执行，API Key 只在 VPS 上隐藏输入）：

```bash
ssh root@199.102.217.22
git clone --branch feature/mia-ios-bootstrap https://github.com/bboytang/Mia.git /root/Mia
bash /root/Mia/server/deploy/install-ubuntu.sh
```

脚本安装 Python、libopus、Caddy 和 systemd 服务，生成随机网关令牌并显示一次供 iPhone 设置使用；它不会覆盖现有 Caddy 配置。若 `git clone` 要求 GitHub 登录，先在 VPS 上用你已有的 GitHub 访问方式取得仓库即可，不要把 GitHub 凭据填进脚本。接着编辑 `/etc/caddy/Caddyfile`，在不删除已有站点的前提下加入 `server/deploy/Caddyfile.example` 的内容，然后运行：

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
systemctl status mia-gateway --no-pager
curl -I https://8kraw.cloud/
cd /root/Mia && . /opt/mia/.venv/bin/activate && python server/deploy/check_wss.py
```

站点根路径返回 404 也可以；握手脚本会验证 TLS、令牌及小智协议，但不会调用百炼 API。若 `80/443` 被防火墙拦截，先在 VPS 和云厂商安全组中放行。更新代码后重新运行脚本会生成**新的**客户端令牌，必须同步更新 iPhone 钥匙串中的令牌。

目前的自动化测试用内存假提供者验证协议与 Opus，不会调用真实 API。需要开通账号并在 VPS 与 iPhone 上实测中文识别、声音、延迟、中断和费用后，才能宣称语音聊天交付完成。
