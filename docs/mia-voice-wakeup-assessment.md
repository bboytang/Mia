# Mia 自定义语音唤醒：iOS 限制评估

2026-10-12。用户希望直接喊“Mia”，包括锁屏或后台；不接受 Siri 替代，本阶段先评估，不实现后台常驻录音。

## 结论

| 场景 | 可行边界 |
| --- | --- |
| App 前台 | 可用设备本地关键词检测。当前先实现打开即聊，无需唤醒词；可另增前台待机模式。 |
| 先在前台开启监听，再锁屏或切到后台 | Apple 的后台音频能力可以让获授权的录音继续。需要持续激活音频会话、后台音频配置、本地唤醒模型和明确的开启/停止入口；仍会受电话、音频中断、系统资源管理影响。必须实际测试，不能保证长期常驻。 |
| App 已挂起、被用户划掉、进程被系统终止，或重启后未打开 | 进程没有正在运行的音频监听，不能靠本 App 的自定义词直接启动。不能把后台录音能力描述成 Siri 式系统级唤醒。 |

Apple 说明：授予录音权限并添加 `UIBackgroundModes=audio` 才能继续后台/锁屏录音，其他音频会话仍可能打断。[record](https://developer.apple.com/documentation/AVFAudio/AVAudioSession/Category-swift.struct/record)、[UIBackgroundModes](https://developer.apple.com/documentation/bundleresources/information-property-list/uibackgroundmodes)。生命周期与进程退出后的边界是根据需要持续运行音频采集和关键词检测推导的实现限制，不是已完成的真机实验。

## 检测方案与成本

- 若进入实施阶段，优先专门的设备本地关键词模型，未唤醒的环境音只做本地检测，不送小智 ASR，不用云端转写长期监听。
- 不能简单把 `SFSpeechRecognizer` 的持续转写当作稳定的唤醒引擎。Apple 要求处理识别服务可用性、时长和资源限制；其文档要求按约一分钟的识别任务限制规划。[SFSpeechRecognizer](https://developer.apple.com/documentation/Speech/SFSpeechRecognizer)。本项目最低 iOS 17，不能默认依赖更高系统版本的新语音能力。
- 需要选定并验证唤醒引擎、iOS 模型、授权/依赖成本，以及“Mia/米娅”发音、误唤醒、外放回声、蓝牙、锁屏时长和耗电。当前未新增引擎、SDK、账号或密钥，未通过任何后台唤醒实验。
- 产品行为需另行确认：谁开启常驻监听、如何明确停止、是否在每次启动恢复、被中断后如何提示。不能为保活播放静音、假装 VoIP 通话或绕过 iOS 的后台管理。

## 当前实现范围

启动动画结束后，仅在前台开始自动对话；首次请求麦克风权限。小智 `listen mode=auto` 自动结束一句话，实际播放结束后继续下一轮。iOS Voice Processing 处理回声，系统 muted speech activity 事件触发本地停止播放与协议 abort。不声明服务端 MCP/AEC 能力。

前台模式进入后台或发生音频中断时清理资源。未添加 `UIBackgroundModes`，未增加 Siri 入口，未实现自定义唤醒词。系统语音检测用于播放中的打断，不是关键词识别。
