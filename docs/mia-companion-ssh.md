# 当前 Mia 工作环境的 SSH 授权恢复

2026-10-13：连接 `ubuntu@43.143.230.174` 仍返回 publickey/password 拒绝，未跳过既有主机校验。当前私钥对应的公钥指纹已核对一致：`SHA256:nOfXTTs+SJGvYLEs7+AWaWiShWUZOC5S4CDj+s24ic4`。

用户要求的授权指令：在服务器控制台、有 sudo 权限的账户执行，追加当前公钥，不覆盖已有授权。

```bash
mia_pubkey='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMewNYfAXUntR7J/w5jZ4G7bEi46fVZhfzOH6R/dfbbN mia-server'

sudo install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
sudo touch /home/ubuntu/.ssh/authorized_keys
sudo grep -qxF "$mia_pubkey" /home/ubuntu/.ssh/authorized_keys ||
  printf '%s\n' "$mia_pubkey" | sudo tee -a /home/ubuntu/.ssh/authorized_keys >/dev/null
sudo chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys
sudo chmod 600 /home/ubuntu/.ssh/authorized_keys
```

执行后通知当前任务，先只读重试并核对部署。此公钥属于当前工作环境；未来环境身份变化时重新核对指纹，不沿用错误的身份。本文没有私钥、密码或服务器令牌。
