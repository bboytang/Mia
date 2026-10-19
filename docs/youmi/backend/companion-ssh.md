# 当前 Youmi 工作环境的 SSH 授权恢复

2026-10-13：用户明确登录账户应为 `root`，现已成功连接 `root@43.143.230.174:22`，保留既有主机校验。此前 `ubuntu` 账户拒绝公钥。当前私钥对应的公钥指纹已核对一致：`SHA256:nOfXTTs+SJGvYLEs7+AWaWiShWUZOC5S4CDj+s24ic4`。

以下是此前针对 ubuntu 的授权指令，仅留作历史记录；当前使用 root 已授权身份，无需重复执行。

```bash
youmi_pubkey='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMewNYfAXUntR7J/w5jZ4G7bEi46fVZhfzOH6R/dfbbN mia-server'

sudo install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
sudo touch /home/ubuntu/.ssh/authorized_keys
sudo grep -qxF "$youmi_pubkey" /home/ubuntu/.ssh/authorized_keys ||
  printf '%s\n' "$youmi_pubkey" | sudo tee -a /home/ubuntu/.ssh/authorized_keys >/dev/null
sudo chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys
sudo chmod 600 /home/ubuntu/.ssh/authorized_keys
```

执行后通知当前任务，先只读重试并核对部署。此公钥属于当前工作环境；未来环境身份变化时重新核对指纹，不沿用错误的身份。本文没有私钥、密码或服务器令牌。
