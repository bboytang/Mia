# Mia 升级交接

更新：2026-10-13。主入口：[批准方案](mia-companion-plan.md)、[分步计划](mia-companion-implementation.md)、[工作记录](mia-companion-worklog.md)。

## 用户已确定

小球完全替代人物；质感优先、科技背景、无字幕；点球控制。系统口令“你好，米娅”；首开待呼叫。
最新补充：口令必须直接在后台开始语音对话，不接受打开App后聊天替代；此前前台回退方案不再作为验收路径。用户明确允许推送后，修复 e46c1d0 已推送并通过原生构建/86单元/4UI和83服务端测试；后台直接唤醒仍未真机验收。[新测试IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-e46c1d098c96/Mia-unsigned.ipa)需同时重签扩展；自然记忆命令补丁现已部署并完成真实保存/重连/检索验证。尚待确认快捷指令App能否发现后台开始动作。
后台直接语音聊天和灵动岛；锁屏 Mia 停麦克风，接受系统声音快捷指令继续监听。
有主见伙伴，性格自然形成，自动记重要内容、敏感先问。沿用现有服务，不训练模型。

## 当前进度

最新服务端：用户要求部署自然记忆补丁，已将Python更新为 `mia-xiaozhi-server:companion-memory-2d153d4`。83项服务端测试通过，真实“米娅，请记住……”无需冒号，在本轮结束前保存、重连读取和实际provider检索通过，测试记录清理后原有9条记忆保留。热备/回滚目录 `mia-memory-natural-20261013-2d153d4`。无需在小智管理页面改变 `Memory_nomem`；Mia认证记忆独立启用。

音色：已将后台现有“豆包语音合成2.0(流式)”型号的占位appid/access_token替换为当前有效型号的两项凭据，原配置受保护备份，保留其他参数和当前智能体的Vivi选择。该型号已有40条音色；湾湾小何和阳光青年真实返回音频。用户在绑定Mia的智能体配置中选择该型号及“声音音色”，保存后结束/重开对话即可。不要从旧测试型号的旧版音色列表任选，因为当前资源是seed-tts-2.0；其余音色和iPhone播放未逐一验证。详见[部署与音色指南](mia-companion-backend.md)。

最新皮肤包：[cb07db0测试IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-cb07db038e4d/Mia-unsigned.ipa)，10,778,899字节。设置→个性化皮肤提供玻璃流体/蓝金星环，默认保留原主题，用户选择持久化。CI38447444188最终91单元/5UI与两种编译/打包/截图通过；图像/提示词见design/mia-holographic-assets.md。新素材为静态球壳/耳环，脸、耳环响应、摇摆及粒子使用原生动画。

用户报告软件完全退出也会误触发系统动作：新增本机系统开始动作次数/最近时间、重复调用保护及重训/自动化检查指引，不能声称修复iOS首次误识别。实际输入嘴形/耳环幅度、后台交接、发热耗电与误触发频率仍待真机；皮肤交付时未部署服务器，随后自然记忆补丁已上线。

客户端和生产后端已实现，真机验收未完成。

- 客户端 `0d9a7cf43a91` 成功CI38395441414：85单测/4UI、模拟器/设备/Widget编译、打包/截图通过。[实际首页](design/mia-companion-home.jpg)、[第二尺寸](design/mia-companion-home-secondary.jpg)。同代码重复标签构建38397666792曾一项ready等待超时，第二次运行单元/UI/设备打包已通过，截图采集进行中，见工作记录。
- [预览IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-0d9a7cf43a91/Mia-unsigned.ipa)：7,476,764字节；SHA256 `11bef6b50fffe56022f8629099f524beb473f771a7095fab476ce81d9b928ed2`。包含Widget/Metal，无启动视频；必须同时重签App/扩展。
- 服务端修复 `40c715de13a020bdea40ee3b466e7678f34df89a`，CI38401621395完整81项成功；真实联调发现的初始化时序和模型代码块格式已修复。
- 已通过原授权密钥与主机校验登录 `root@43.143.230.174:22`。生产Python源码与v0.9.7匹配，原Java目标class与原源码构建逐字节一致；补丁JAR只改变目标class。
- 运行 `mia-xiaozhi-server:companion-memory-2d153d4` / `mia-xiaozhi-web:companion-0d9a7cf`，原MySQL/Redis/认证/密钥/绑定保留。持久DB `/opt/xiaozhi-server/data/mia-memory.sqlite3`，权限600。
- 真实绑定设备即时管理、现有模型提炼、重连读取、暂停/恢复、删除通过；独立owner重启持久验证通过，临时记录已清理。ASR/VAD自动断句/TTS通过，未用iPhone麦克风。
- 三合成情境实际返回 caring/sad/calm；测试期间暂停记忆、每轮恢复，不训练合成性格。此前长连接探针正常关闭，改独立连接后完成，不当作八情绪人工验收。
- 暂存/构建/回滚 `/opt/xiaozhi-server/mia-deploy-20261013`；backup内保留原JAR/core/compose/配置/MySQL导出和SQLite热备。维护需同时使用原compose、lowmem和mia覆盖文件，见[部署指南](mia-companion-backend.md)。
- 本地Linux无Xcode；[30分钟真机清单](mia-companion-device-check.md)仍待iPhone14 Pro Max/iOS27执行。

## 接续规则

- 看分步表和工作记录，继续当前步骤，不重复已完成工作；完成一步即追加结果和剩余项。
- 服务端接实际小智，不迁回旧网关；配置/密钥值不可输出。客户端身份不能作为任意 owner。
- App 后台/锁屏、系统监听交接与重签扩展都需真机；不能只凭构建或模拟器宣称满足。
- 声音快捷指令须用户在系统设置训练；开发者模式不能解除系统限制。
- 采用已有保护数据事件只能近似锁屏检测，不虚构可靠的公开屏幕通知。
- 不自动上线未经真机验收的后台/锁屏承诺。代码回滚不清除记忆或设备绑定。

## 下一步

已发布IPA无需因服务端修复重新打包。用户在绑定Mia的智能体配置中选择2.0音色，保存后结束/重新开聊；按真机清单验收记忆页面、后台/锁屏/声音快捷指令、情绪、发热和耗电。不得把服务部署或模拟器成功称为这些系统行为已满足。
正常维护保留 `docker-compose.mia.yml`；回滚只切换两服务原镜像，不清除记忆和绑定。
