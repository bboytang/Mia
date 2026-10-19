# iPhone 安全连接与客户端补交付

用户指出后端部署之后没有收到新版 iPhone 客户端。本次以独立 IPA 的实际下载交付为准，不把后端部署或源码存在算作客户端交付。

此前已存在 `2d2c1bf` 的个人测试包，但与此次修复前的 iOS 目录相同，默认地址仍为明文 `ws://43.143.230.174:8000/xiaozhi/v1/` 和 `http://43.143.230.174:8002/xiaozhi/ota/`。当前语音服务已启用 TLS，私有授权也要求 HTTPS/WSS，旧默认值不能作为当前可用连接配置。

本次代码 `fc488d0bd499d863aa036203c963730c1954a7eb`：默认改为 `wss://43.143.230.174:8000/xiaozhi/v1/` 和 `https://43.143.230.174/xiaozhi/ota/`。控制器在构造会话前迁移这两个精确旧值，自定义服务器保持原值；不改变设备 MAC、client UUID、Keychain 凭据、角色、模型或皮肤。新测试覆盖 HTTPS 私有授权路由、旧地址迁移的幂等性、身份保留与自定义服务器保留。公开 HTTPS OTA 路由已完成证书验证的只读 GET 检查，不把它当作 iPhone 录音验收。

安装仍沿用未签名 IPA 的分发方式。需要使用原签名、原 Bundle ID 覆盖安装，保留并签名 `PlugIns/YoumiActivity.appex`；不卸载清除已有本机数据。尚未完成私有授权时，在已登录智控台为该 iPhone 的已绑定设备生成一次性码，再到 App 设置中的“私有授权”兑换。硬件六位确认码不用于 iPhone 兑换。

本次不修改生产后端、不创建生产数据备份，也不在包中加入用户密码、服务器密钥或设备私有凭据。实际 iPhone 录音、扬声器、耳机、后台唤醒和灵动岛仍需安装后验收。

已完成交付（2026-10-19）：[直接下载独立 IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-fc488d0bd499/Mia-unsigned.ipa)，10,898,785 字节，约 10.9 MB。SHA-256 `75cc527216b3ff3263827928c5778d3cf23f8cc847fb3008302f8e14803d5dca`。

[同提交完整 iOS CI](https://github.com/bboytang/Mia/actions/runs/39265843521)通过 104 项单元测试、6 项 UI 测试、模拟器与 unsigned 设备/Widget 编译、扩展与快捷动作打包检查，以及两种屏幕尺寸预览录制。本次预览步骤耗时较长，但最终成功，无跳过或降低验证范围。发布后回下载 IPA 并核对 SHA-256，与 CI 产物一致；ZIP 完整性、主 App 与 Widget 的 Bundle ID、安全默认 URL 的设备二进制字符串、iOS 17.0 最低版本均已核对。原 iOS 个人测试发布与其校验文件保留，不覆盖。

公开脱敏记录见 [verification/mia-ios-secure-delivery](../../verification/mia-ios-secure-delivery)。
