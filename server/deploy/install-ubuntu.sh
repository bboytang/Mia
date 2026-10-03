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

read -r -s -p '输入北京地域百炼 API Key（输入不回显）：' dashscope_key
echo
if [[ ! $dashscope_key =~ ^sk-[A-Za-z0-9_.-]+$ ]]; then
  echo 'API Key 格式不符合预期，未写入配置。' >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv libopus0 caddy
gateway_token=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
getent group mia >/dev/null || groupadd --system mia
id -u mia >/dev/null 2>&1 || useradd --system --gid mia --home /opt/mia --shell /usr/sbin/nologin mia
install -d -o mia -g mia /opt/mia
cp -a "$repo_dir/server" /opt/mia/
chown -R mia:mia /opt/mia/server
runuser -u mia -- python3 -m venv /opt/mia/.venv
runuser -u mia -- /opt/mia/.venv/bin/python -m pip install -r /opt/mia/server/requirements.txt

install -d -m 700 /etc/mia
umask 077
cat > /etc/mia/gateway.env <<EOF
DASHSCOPE_API_KEY=$dashscope_key
MIA_BAILIAN_REGION=cn-beijing
MIA_GATEWAY_TOKEN=$gateway_token
EOF
chmod 600 /etc/mia/gateway.env
install -m 644 "$repo_dir/server/deploy/mia-gateway.service.example" /etc/systemd/system/mia-gateway.service
systemctl daemon-reload
systemctl enable mia-gateway
systemctl restart mia-gateway

echo '网关已安装。请按 server/README.md 配置 Caddy 的 8kraw.cloud 站点并开放 80/443 端口。'
echo "iPhone 客户端访问令牌：$gateway_token"
