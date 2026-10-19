# Mia 个人测试版本

2026-10-19。优先一个人的日常使用，保留现有SQLite、BGE、GLM和安全校验。原P23多人压力与首句指标仍按历史结果记录，本版本不宣称P23通过。

当前已部署 `aebec000d864160963e01b0be9fcf9ff7dcab8b9`。四项同SHA CI均通过：[367项服务测试](https://github.com/bboytang/Mia/actions/runs/39208658664)、[175项身份测试](https://github.com/bboytang/Mia/actions/runs/39208658659)、[manager](https://github.com/bboytang/Mia/actions/runs/39208658655)、[真实BGE/提取/上下文](https://github.com/bboytang/Mia/actions/runs/39208658619)。22个线上文件hash匹配，HTTPS/WSS就绪，更新前后47事实/47向量、完整性正常，无新增备份或数据改写。

用户确认正常连续聊天、两条偏好自动保存和重启后召回；期间实际发生同会话说话者串错，不能称全部召回都准确。此次只标注模型请求里的历史Mia回复，原对话/来源/安全不变。70+31本地定向测试与最后3例固定真实GLM重放通过，之前两种无效方案失败证据保留；共12真实SDK/HTTP、隐式重试0，非稳定性统计。部署后同会话追问待用户确认。详见[说话者复核](verification/mia-persona-memory/personal-speaker-history-review.json)。

音频连接复用已上线，每个音频包仍实时复核权限；固定13次复核首73.47ms、其后4.78–7.73ms。是否消除实际通话般断续仍待用户明确反馈，不称音频验收通过。固件仍1.0.3，不需重新授权；[iPhone个人包](https://github.com/bboytang/Mia/releases/tag/mia-personal-ios-20261019-2d2c1bf)需个人签名，未验证iPhone实机音频。真实硬件纠正/删除仍只具有先前隔离单用户端到端证据，天气API鉴权故障另记，不冒充现有全部功能通过。

以下保留历史过程和异SHA证据，当前状态以顶部及末尾最新记录为准。

当前检查点：私有语音后端已部署 `f1da36fdbb1c1997d170d953f27e28544b18dbf5`，硬件1.0.3已授权。WSS证书校验及101、原45事实指纹保持、V4迁移/45真实BGE向量通过。实机已经有声，但旧8192硬编码预算触发完整硬件工具超限，声音是安全兜底；最新修复后用户已确认正常连续有声聊天；两条真实偏好自动保存并同步向量，现47事实/47向量，两任务attempt1/2分别4/7秒，共3次实际HTTP，含一次来源语义拒绝后有效重试。四项同SHA CI均成功、服务361测试。跨会话实机召回等待反馈，纠正/删除及再一次生产进程重启未重复实测，与原隔离端到端通过证据分列。个人服务器明确输入预算24576、保守GLM窗口32768及回复2048，绑定原Provider/endpoint/model，原测试默认8192与全部安全检查保持；P23不改判。以下部署准备和未切换描述保留为历史过程。

最新部署状态（下文旧检查点仅作历史）：HTTPS、硬件授权后台及网页已部署；1.0.3 签名 OTA 已上传原升级接口并验证实际下载 hash。1.0.2 已被设备实际安装，但用户指出32位码无法完整显示；该实机失败及原发布包保留。现改成6位数字，设备私有128位证明不显示、不进入公开固件，六位码本身不能兑换凭据。等待用户重启至1.0.3并在原设备页确认后，才切换私有记忆语音后端，避免提前中断旧固件启动健康检查。

授权后台/网页源码 `a7c5024789e0c91df8e0a1d7d4a1cb3ae48ed272`：[身份175测试](https://github.com/bboytang/Mia/actions/runs/39202577821)、[manager](https://github.com/bboytang/Mia/actions/runs/39202577830)、[服务](https://github.com/bboytang/Mia/actions/runs/39202577833)、[网页](https://github.com/bboytang/Mia/actions/runs/39202577825)均通过。固件 `65d77063753cc845ab60e3db5357ee42aad5a1dc`：[126主机测试及五构建](https://github.com/bboytang/Mia/actions/runs/39202578805)通过；[1.0.3 OTA 包](https://github.com/bboytang/Mia/releases/tag/mia-passport-1.0.3-ota-65d7706)序列4，签名、冻结分区/资源和原更新器A→B主机模拟通过，尚不代表1.0.3实机授权或音频通过。

[iPhone个人包已发布](https://github.com/bboytang/Mia/releases/tag/mia-personal-ios-20261019-2d2c1bf)，仍需自己的签名及Widget重签。实际硬件与近期iPhone绑定同一智能体，未为测试重绑或合并数据。生产实际2CPU、约1.9GiB且已有swapfile，不冒称正式swap0性能验收。无新增备份；原SQLite、旧OTA和全部失败证据保留。

## 当前候选与验证

当前运行候选 `006c6f77709bea6eaed21cea79bb45cd5946a1dd`。复用原行为测试完成一用户流程；修正已有观察器及明确口误纠正路径，没有新增架构或测试框架。

- [单用户真实GLM/BGE/SQLite流程](https://github.com/bboytang/Mia/actions/runs/39197016530)：`ed9afd911528b311a33106819cce3787172d5d7e` 通过。7次回复SDK、1次提取SDK/1次提取HTTP；明确口误经既有确定性路径校验提交，纠正任务attempt0/SDK0。三个真实进程、两次重启，删除后事实0。首模型内容0.767–1.677秒，整回复1.123–2.322秒；不代表实际音频延迟或正式p95。
- 其后的 `006c6f7` 仅补旧数据库NULL元数据的输入兼容及反例，99项相关本地测试通过；未重复采样真实模型，不把前一SHA流程冒充当前SHA实测。五项必要同SHA CI均已终态成功：[服务](https://github.com/bboytang/Mia/actions/runs/39197588881)、[身份授权](https://github.com/bboytang/Mia/actions/runs/39197588973)、[manager](https://github.com/bboytang/Mia/actions/runs/39197589073)、[真实BGE](https://github.com/bboytang/Mia/actions/runs/39197588875)、[结构化提取](https://github.com/bboytang/Mia/actions/runs/39197589042)。
- 首四轮失败的原始JSON、SQLite与hash分别保留为 `verification/mia-persona-memory/personal-*-failed-*`；通过证据为 `personal-passed-*`。模型非法来源仍拒绝，没有以放宽校验取得通过。旧关系事件激活要求未由个人流程证明通过。
- [iPhone原生测试与安装包构建](https://github.com/bboytang/Mia/actions/runs/39195183918)：成功，102项单元及6项UI测试通过，模拟器与unsigned设备/Widget构建成功。iOS源码来自 `2d2c1bf41d1683bb49c44e4794270d23e47d2dbd`，之后到当前运行候选的iOS目录字节未变，没有重复构建。
- 本地在全新固定上游副本执行companion与identity两个安装器的check/apply，四步及安装后Python语法通过；没有连接或迁移真实数据库。副本 `/tmp/mia-personal-install-zbv42bt1`。

单用户流程复用历史自然纠错第一组：人格身份→短暂陪伴（不存长期事实）→普通叙述蓝色通勤自行车（自动存储、来源保留）→新连接召回→自然纠正为银色（同一事实更新）→进程重启后按新说法召回→所有者删除→第二次进程重启后不能召回。测试桥调用安装后原chat/Worker/manager，输出进现有安全TTS文本队列；不包含ASR、实际合成音频或设备播放。记录首模型内容与整轮耗时，不把它当正式首句p95。

## 两种设备

**iPhone**：已准备unsigned IPA，10898413字节，SHA256 `8ea0fd6007c78c2ba6102422514f81313e4a3c46c706d3d8270c6d1b65aa2c53`。本机交付目录 `/tmp/mia-personal-delivery/` 含IPA、SHA256SUMS及manifest；尚未发布新的下载release。需要沿用自己的签名及Bundle ID，同时重签MiaActivity.appex。保持现有设置及绑定，不卸载清空。个性化记忆需manager HTTPS／语音WSS和本机私有授权（设置→私有授权，用智控台一次性码），不复制其他设备凭据。

**Mia硬件**：已从仓库及发布记录确认 FoLoToy AI Passport、ESP32-C3、8MB Flash。昨晚发布固件源码 `9083560e489f866380c4ff49bc2bcbcab393c518`，型号 `mia-ai-passport`；[现有1.0.1 OTA试用包](https://github.com/bboytang/Mia/releases/tag/mia-passport-1.0.1-ota-9083560)。用户确认昨晚已刷并连通，具体在机版本尚未远程读取。本轮不重刷bootloader/分区/资源、不合并独立硬件分支、不要求为服务端测试重复刷机。

已核对实际已发布固件：发送Bearer、Device-Id、Client-Id，尚无Mia-Private-Credential；其冻结入口是HTTP/WS。新记忆后端要求TLS及本设备私有授权，因此现有普通语音连通不能证明新版记忆可用。后端上线前须完成兼容接入，不能在固件未适配时直接把现有服务替换成要求新凭据的版本。保留昨晚已连通版本。

用户已明确选择OTA路径，不要求USB。签名OTA可以补授权代码；不能把长期凭据放进公开固件、经HTTP下发或仅凭MAC自动授予Scope。实际授权接入尚未实现，不将“支持签名OTA”描述成“记忆授权已完成”。独立固件工作区 `/tmp/mia-passport-personal` 基于昨晚发布的9083560，尚无改动，固定记忆工作分支未切换。

## 安装前的实际边界

**新版尚未部署，部署已获明确授权，无需再次确认。** 用户最新明确要求不再备份；停止新增备份，不因本任务复制现有生产数据。刚才的备份命令被执行环境自动审批服务拒绝启动，没有生成该备份。

已只读核对生产：两服务仍为 `responsive-20261014T134645Z-a30a508`，SQLite45条事实/2个owner；八个待更新Python源码hash与可重建旧基线一致。依赖已满足OpenAI2.8.1/httpx0.28.1/numpy1.26.4/onnxruntime1.23.2，但尚无tokenizers。没有改变已有事实、配置或绑定，没有重启服务。已安装隔离certbot工具并申请IP证书，有效至2026-10-25；证书仅暂存，尚无443反向代理或续期timer，不得据此称HTTPS已上线。

当前执行阻塞：自动审批服务间歇报模型容量不足/超时，后续SSH命令未执行；这是执行服务故障，不是用户授权不足，也不是判定部署不安全。2026-10-19已成功补取一次只读依赖/nginx检查，后续检查仍未启动。恢复后继续部署，无需重问授权；先完成TLS入口与续期、旧库兼容与索引、硬件授权接入，再切换并实际验证。新代码启动会执行已有SQLite版本迁移，不能把直接挂载生产数据库的试运行当只读验证。旧数据线索NULL已兼容；旧事实还需真实BGE索引，不能只迁移表就宣称可召回。

安装包准备不包含真实数据库、密钥、Wi-Fi或设备凭据。后端源码包从固定提交导出，仅供独立暂存环境；使用固定上游 `87c6df77b0220ddbd8fc804f984f83f69f3225e5`，依次执行 `server.companion.install_xiaozhi`、`server.companion.install_identity` 的check/apply，拒绝覆盖已有自定义源码。BGE使用既定离线资产，不在语音进程下载。不得按旧部署文档直接降级旧Worker：V4库需要V2-aware代码，先收敛任务，保留账本和数据。

## 设备上十分钟试用

1. 连续聊三轮，确认有声、不断句卡死，结束后可再次开始；耳机及硬件扬声器分别听一次。
2. 随口说一个真实、非敏感且愿意保留的偏好，等任务结束，在记忆页确认内容和来源。
3. 结束重连后换一种问法，确认召回准确，不编造其他经历。
4. 纠正刚才的偏好，确认记忆页真正更新；重启服务后再次询问。服务重启由部署批准后的维护执行。
5. 删除该条，重连与重启后再问，确认不复现。Mia人设、其他已有记忆和功能应保留。

真实音频流畅度、iPhone后台/耳机、硬件播放以及两设备记忆是否属于同一manager用户/智能体，仍需实际连接核对；不为了测试修改已有归属。

## 2026-10-19 部署继续：HTTPS检查点

执行通道已恢复，用户要求不新增备份继续有效。已实际部署 `mia-xiaozhi-web:personal-tls-006c6f7`，父镜像为原responsive版本，仅替换nginx入口；保留原JAR、前端与语音容器。外部 `https://43.143.230.174/` 返回200、TLS校验0；`mia-personal-certificate.timer` 已active，每日两次检查短证书续期。nginx覆盖客户端传入的Forwarded/X-Forwarded信息，HTTPS状态由实际连接产生。生产复用原三个Compose并追加 `/opt/xiaozhi-server/mia-personal-prep/docker-compose.tls.yml`，后续不能遗漏该覆盖。没有生成备份。

硬件授权最小改动复用原所有者code/exchange接口及原MySQL授权表：固件产生128位随机一次性码，所有者在已有设备页输入确认，再由设备经TLS兑换；同一600秒有效期、单次消费、当前绑定/权限、hash存储及原凭据版本机制不变。新增Java真实接口反例和浏览器交互验证；30项本地授权/安装回归、两个安装器源检查、JS语法与diff通过，Java与浏览器实际验证待本次必要CI。尚未切换记忆后端或发布新版固件，不把HTTPS成功冒充两端记忆可用。
