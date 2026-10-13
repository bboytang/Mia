# Mia 升级交接

更新：2026-10-13。主入口：[批准方案](mia-companion-plan.md)、[分步计划](mia-companion-implementation.md)、[工作记录](mia-companion-worklog.md)。

## 用户已确定

小球完全替代人物；质感优先、科技背景、无字幕；点球控制。系统口令“你好，米娅”；首开待呼叫。
后台直接语音聊天和灵动岛；锁屏 Mia 停麦克风，接受系统声音快捷指令继续监听。
有主见伙伴，性格自然形成，自动记重要内容、敏感先问。沿用现有服务，不训练模型。

## 当前进度

实施已授权。工作树起始干净，步骤 0 完成；系统入口/视觉/记忆存储代码已完成，主任务集成与验证中。
记忆核心/小智适配器29项专门单测通过；公开0.9.7四文件安装补丁预检通过，部署步骤见[服务端指南](mia-companion-backend.md)。
App/Widget模拟器与设备编译、84项原生单测、4UI、IPA打包、两种尺寸截图已通过（d2d5da4/CI38393944549）。实际截图保存[首页](design/mia-companion-home.jpg)和[第二尺寸](design/mia-companion-home-secondary.jpg)。
最终0d9a7cf包含成长依据、管理先停旧对话和跨连接删除保护；其服务端CI38395441408（79测试）和原生CI38395441414（85单测/4UI、两种编译、扩展、打包和截图）全部成功。
已验证代码标签 mia-ios-0d9a7cf43a91已推送，[发布工作流38397708736](https://github.com/bboytang/Mia/actions/runs/38397708736)成功。
[单独预览IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-0d9a7cf43a91/Mia-unsigned.ipa)：7,476,764字节；SHA256 `11bef6b50fffe56022f8629099f524beb473f771a7095fab476ce81d9b928ed2`。回下载包含Widget/Metal、无启动视频。必须同时重签扩展。
没有将旧网关当实际服务。用户纠正登录账户后，root SSH 已恢复；生产预检与备份完成，管理服务隔离构建中，尚未切换生产。
用户要求授权命令，已提供当前环境公钥追加脚本；公钥指纹 SHA256:nOfXTTs+SJGvYLEs7+AWaWiShWUZOC5S4CDj+s24ic4，已通过 root 账户登录。
完整命令见[SSH恢复说明](mia-companion-ssh.md)。
本地 Linux 无 Xcode；原生 CI 已成功，设备测试尚待运行。

## 接续规则

- 看分步表和工作记录，继续当前步骤，不重复已完成工作；完成一步即追加结果和剩余项。
- 服务端接实际小智，不迁回旧网关；配置/密钥值不可输出。客户端身份不能作为任意 owner。
- App 后台/锁屏、系统监听交接与重签扩展都需真机；不能只凭构建或模拟器宣称满足。
- 声音快捷指令须用户在系统设置训练；开发者模式不能解除系统限制。
- 采用已有保护数据事件只能近似锁屏检测，不虚构可靠的公开屏幕通知。
- 不自动上线未经真机验收的后台/锁屏承诺。代码回滚不清除记忆或设备绑定。

## 下一步

IPA发布与校验已记录；root SSH已恢复，生产预检/备份完成，隔离管理构建进行中。暂存目录 `/opt/xiaozhi-server/mia-deploy-20261013`，先验证原始class一致，再编译补丁并仅替换一份class，随后构建镜像、按原compose启动与联调。原生/服务端代码已验证，不需重复重写。
生产记忆未部署，后台/锁屏/语音交接与[30分钟真机清单](mia-companion-device-check.md)未验；不得标为全部完成。
