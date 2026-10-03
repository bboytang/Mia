#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo '请在 Ubuntu VPS 上以 root 运行此脚本。' >&2
  exit 1
fi

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ ! -f "$repo_dir/server/requirements.txt" ]]; then
  echo '请从 Mia 仓库中运行此脚本。' >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv libopus0 caddy
getent group mia >/dev/null || groupadd --system mia
id -u mia >/dev/null 2>&1 || useradd --system --gid mia --home /opt/mia --shell /usr/sbin/nologin mia
install -d -o mia -g mia /opt/mia
cp -a "$repo_dir/server" /opt/mia/
chown -R mia:mia /opt/mia/server
runuser -u mia -- python3 -m venv /opt/mia/.venv
runuser -u mia -- /opt/mia/.venv/bin/python -m pip install -r /opt/mia/server/requirements.txt

install -d -m 700 /etc/mia
umask 077
if [[ ! -f /etc/mia/gateway.env ]]; then
  gateway_token=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  printf 'MIA_GATEWAY_TOKEN=%s\n' "$gateway_token" > /etc/mia/gateway.env
  echo '新网关令牌已生成；请只在私有终端查看 /etc/mia/gateway.env。'
fi
for setting in \
  'MIA_PROVIDER=volcengine' \
  'VOLC_ARK_API_KEY=' \
  'VOLC_VOICE_API_KEY=' \
  'MIA_CHAT_MODEL=doubao-seed-2-1-lite-260915' \
  'MIA_ASR_RESOURCE_ID=volc.seedasr.sauc.duration' \
  'MIA_TTS_RESOURCE_ID=seed-tts-2.0'; do
  name=${setting%%=*}
  if ! grep -q "^${name}=" /etc/mia/gateway.env; then
    printf '%s\n' "$setting" >> /etc/mia/gateway.env
  fi
done
chmod 600 /etc/mia/gateway.env
install -m 644 "$repo_dir/server/deploy/mia-gateway.service.example" /etc/systemd/system/mia-gateway.service
systemctl daemon-reload
systemctl enable mia-gateway

echo '火山网关代码和空白 Key 字段已部署；现有服务未重启。设置两把 Key 后重启并验证服务。'
