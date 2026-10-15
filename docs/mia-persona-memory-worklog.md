# Mia 人格认知与长期记忆：工作记录

方案：[V1.2](mia-persona-memory-v1.2.md)。步骤：[完整实施计划](mia-persona-memory-implementation.md)。当前状态：[交接入口](mia-persona-memory-handoff.md)。

本文件按实际发生追加。计划步骤、未执行命令、未测试选型不能写成已完成事实。记录采用仓库相对路径、完整 SHA 和稳定证据定位；不放令牌、密码、私钥、原始生产用户对话或数据库。

## 2026-10-14：V1.2 与 P00 接续文档

- 用户范围：仅修订开发方案和完整计划，本轮不开始代码开发或部署。
- 从用户指定对话核对 V1.1 原文，形成 V1.2；四项约束为核心机制保留、完整向量 RAG、必要身份链整改边界及八项真实行为验收。
- 文档基线：`feature/admin-responsive`，源码 `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`。原 V1.1 的审核基线与当前工作树基线在方案中分别记录。
- P00：整理 P00—P28、D01—D10、B01—B08；加入跨设备／环境／账号恢复、版本与权限核对、进度和证据记录、待完成 run／操作恢复及接续说明。
- 产物：`docs/mia-persona-memory-v1.2.md`、`docs/mia-persona-memory-implementation.md`、`docs/mia-persona-memory-handoff.md`、本文件。
- 验证范围：文档内容、步骤／链接一致性和差异检查；不表示软件能力通过。没有执行软件测试／构建、真实模型／embedding 实验、远程认证核查或硬件验收。
- 保存状态：四份文档尚未提交、推送。P01 跨设备持久取得验证未执行；不能宣称新设备拉取远程即可取得本轮文档。
- D01—D10：均未冻结；B01—B08：代码、机制、真实行为及真机验收均尚未开始／执行。
- 下一步：在对应范围明确后执行 P01；后续获准开发再按环境、基线和决策顺序推进。

## 2026-10-14：开始执行，P01 进行中

- 用户明确要求开始计划，并每完成一步更新交接和进度；开发与任务 Git 保存已授权，尚未执行生产变更。
- 只读检查：原工作树仅有本任务四份未跟踪文档；源码为 `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`。
- 在允许网络的执行环境，`git ls-remote` 核对远程 `feature/admin-responsive` 与当前 SHA 一致，旧 iOS 分支为原审核 SHA；GitHub 仓库实际查询显示读取／推送权限正常。
- 已从当前基线创建 `feature/mia-persona-memory-v1.2`，原分支和其他工作保留；仅定向保存任务文档。
- 受限 shell 的 GitHub DNS／gh 状态曾失败，联网执行环境同一实际请求成功；没有重新登录或更换令牌。
- 下一步：推送文档，从独立目录检查远程精确 SHA 与四文件内容，验证后登记 P01 完成，再开始 P02。

## 2026-10-14：P01 完成，计划已可跨设备取得

- 自动审批首次拒绝包含 push 的组合命令，原因是缺少具体内容及远程目的地确认；该命令未执行。先单独在本地保存，没有通过其他工具绕过上传拒绝。
- 用户随后明确允许四份文档及后续开发代码／验证记录推送到 `bboytang/Mia` 的 `feature/mia-persona-memory-v1.2`。
- 提交 `d74b89acc0973502234724fba0e681b112985eeb` 已推送；独立浅克隆检出相同 SHA，四份文档逐字节一致。仅创建任务分支，原管理后台分支保留。
- 下一步：P02 环境及访问核实。文档已远程取得不等于开发能力或生产发布完成。

## 2026-10-14：P02 完成，环境与访问缺项已明确

- 证据：`docs/verification/mia-persona-memory/environment.md`。
- 实际核实 GitHub repository 读写、active Actions 和原身份严格主机校验的服务器只读 SSH；未重新登录、重置令牌或追加 SSH key。
- 本地 Java／Maven／Xcode 和协议依赖缺失；软件测试／构建全部保持在 GitHub。服务器运行 Python 3.10.22／Java 21，不以本地 Python 3.12 替代运行兼容性验证。
- 仓库 Actions secrets 返回 0；组织／environment secrets 未核实。真实聊天 Provider 测试凭据和 iOS 真机／签名仍属后续缺项。
- 下一步：P03 固定实际源码／运行补丁；缺测试凭据不阻止无远程模型密钥的 embedding 实验准备。

## 2026-10-14：P03 完成，D01 固定实际组合

- 证据：`docs/verification/mia-persona-memory/baseline.md`、`runtime-baseline-20261014.json`、`manager-baseline-20261014.json`。
- 固定 Mia 基础 SHA `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`、上游基础 `87c6df77b0220ddbd8fc804f984f83f69f3225e5` 和五项官方修复来源 `27399a2fb64b5910196f438a256ce0a9f868481f`。
- 现网三份记忆模块与仓库逐文件校验一致；五项官方修复与 manifest after 一致；音乐精确匹配挂载保留。读取表字段未读取用户内容。
- 当前实际镜像为 responsive-20261014T134645Z-a30a508 组合，约 2 核／1941 MiB，不继续使用早期记忆镜像作为发布起点。
- Java 指定四类校验值已采集；与新的真实 Java 构建逐字节对照留 P07，不声称已完成。
- 基线已有 GitHub 服务端、官方修复、管理后台成功结果；本次服务端 run `38582489146` 亦成功。一次查结果与 dispatch 同命令导致不必要重复，尝试取消时已经完成；后续先读取再判断。未运行本地／服务器自动化测试或构建。
- 下一步：P04 固定样本与指标，P05 契约，P06 候选实际比较。

## 2026-10-14：P04 准备及 D07 用户决定

- 首份检索样本 `server/tests/fixtures/persona_memory_retrieval_zh.json`：20 条合成记忆、36 个中文查询，区分校准与留出；包含其他用户／角色、被替代／删除、跨措辞、关联和空召回。未运行检索实验，不声称模型达到质量门槛。
- D07 窗口／保留／停用语义：用户明确采用最近 30 天分析、最多 90 天观察保留；停用后停止采集和使用，可保留供查看或选择删除，默认关闭保持。
- 其余指标与观察资格将在契约中明确；实际长期行为仍需跨时间验收，不能用单测时钟替代。

## 2026-10-14：P04 完成，D08／D09 验收 v1 冻结

- `docs/verification/mia-persona-memory/acceptance.md`：固定中文留出质量、空召回、零越权／失效召回、2 CPU／2 GiB 实验、延迟／RSS／任务／关闭门槛和八项真实行为场景。
- 样本扩为 20 条合成记忆、72 个查询：校准 16 正向／8 空召回，留出 32 正向／16 空召回；阈值只用校准集。
- 长期真实行为要求至少七自然日、三会话、五有效观察；模拟时钟仅用于机制测试。不能以候选筛选实验宣称八项通过。
- 这些是测试前门槛，不是测量结果；失败后不降低 v1 门槛。需要新算法验收时新增独立留出版本，保留原结果。
- 下一步：P05 契约，P06 实际候选实验。

## 2026-10-14：P05／P06 准备

- D02 待用户取舍：建议在现有智控台登录后为已有绑定签发一次性授权码，App 兑换私有凭据；备选 App 内复用 manager 登录。保留设备 ID 和原绑定，不重建账号系统。
- 公网 TLS：只读 ss 检查当前服务器无 80／443 监听，App 源码默认 HTTP／WS；已询问现有 HTTPS/WSS 域名或入口，未改变监听／配置。
- 公开候选固定 BAAI BGE small／base 的完整 revision；阅读发布者模型说明与官方 ONNX 量化文档，不按榜单直接选型。
- 编写隔离 GitHub 实验：真实 FP32／INT8 向量、CLS／归一化、Scope 内 SQLite 查询、关联／四维、仅校准集阈值、留出／消融、2 CPU／2 GiB 资源与容量。
- 本地仅编写与检查差异；尚未运行软件测试／导出／推理或调用聊天模型。当前没有 eligible 结果，P06 未完成。

## 2026-10-14：P05 完成，开发契约确定

- 用户明确采用智控台一次性授权码；保留设备 ID／绑定，不新增 App 账号登录或第二账户系统。
- D02、D05、D06、D07、D10 见 `docs/verification/mia-persona-memory/contracts.md`：Scope、事实／来源／派生结构、历史与预算、持久任务、事件资格、授权趋势及生命周期。
- 用户询问是否必须域名。核对 Let's Encrypt 当前官方说明：可信 IP 证书可以支持 HTTPS/WSS，160 小时需自动续期，域名不是代码先决条件；未申请证书、开端口或改运行配置。具体部署方案后续核实。
- P05 只是契约完成；真实 Java 身份安全、TLS 运行、schema 与八项行为均未因此标为完成。

## 2026-10-14：P06 首轮真实实验完成，未通过选型

- 代码／样本提交 `3e4ffc6a2794abfb64c70df41ed00c4fa47e5b16`。GitHub 真实 embedding run `38585421342` success；四个报告 eligible 均 false，原结果持久保存为 `embedding-results-v1.json`。
- BGE small FP32／INT8 的留出完整 Recall@4 为 0.90625、Top1 为 0.90625，但空召回 0.875 未达 0.95。BGE base 两变体还有正向质量／资源问题；没有因 workflow 绿色直接选型。
- 一般性问题：扩展词参与 L 产生自证匹配；底线仅用扩展语义；量化一致性没有单独检查；可选 50k 峰值误影响必测 10k 门槛。
- 修正为原查询词法／语义底线、原与扩展有界候选；两次 embedding 计时；原始 PyTorch 向量一致性；仅常量 MatMul 量化；必测与探索 RSS 分开。
- 新独立 v2 合成语料／留出集在执行前冻结，首轮 v1 不改写；质量门槛不变。未本地运行软件测试或模型。
- 同提交服务端回归 `38585420858`：90 项通过（16.745 秒）。这是现有协议回归，不代替新功能真实验收。
- 下一步：提交并运行修正实验，检查真实报告和一致性；不合格继续保持 P06 未完成。

## 2026-10-14：P06 v2 结果与验收语义澄清，P07 独立准备

- 修正实验提交 `0449dd6cfdd405aba59d77bc6ddc3ed77631187e`；真实 run `38587797504` success，四份报告仍 eligible=false，保存 `embedding-results-v2.json`。同提交服务端回归 `38587797471` success。
- BGE small 两变体 v2 空召回 1.0、正向完整 Recall@4 0.8125，必测峰值约 201／237 MiB、p95 约 11／19 ms。未选型，不降低质量门槛。
- 向量参考检查暴露 exporter 的状态问题：外层包装默认 training=True，torch.onnx.export 的状态恢复使内层 PyTorch 参考运行启用 dropout。已改包装 eval 并在参考生成前再次 eval；这影响参考测量，不能据旧参考余弦直接宣称 FP32 ONNX 有精度缺陷，修正后需 GitHub 复核。
- 已询问一项真实验收语义：同主题但缺所问属性（现居城市与出生地）是否允许相关召回但回答明确信息不足。真正无关仍必须空召回。此决定影响检索负例分类，不静默改旧失败记录或用相关事实推断答案。
- 校准置信度探索在工作树中，尚未验证、未选为生产算法；不得因探索存在标 P06 完成。
- 独立准备 P07 Java 基线 workflow：固定上游、重现已有 companion 补丁、真实 Java 编译／现有回归与四类字节校验。它只验证构建基线，不替代后续真实签发／绑定安全集成。

## 2026-10-14：D09 回答边界确认，P06 v3 与 P07 复核

- 用户明确允许相关事实召回，但缺所问属性时必须明确信息不足、不推断；真正无关问题仍要求空召回。验收文档更新 v1.1，数值质量门槛保持，旧 v1／v2 数据和失败记录不重写。
- v3 独立数据：20 条合成记忆、112 查询（校准 24 正向／8 无关／8 相关不可回答；留出 48 正向／16 无关／8 相关不可回答）。检索实验分别报告，实际未知属性回答留真实 Provider，未执行。
- 修正 exporter eval，并以校准集探索原始语义及候选分差拒绝机制；尚未运行，不预先选型。
- P07 首轮 `74d89641f9516f00e3e83520f3972599f837bd76`，run [38590737953](https://github.com/bboytang/Mia/actions/runs/38590737953) 编译及四类字节校验通过。日志实际为 `Tests are skipped`，上游 POM 默认 skipTests=true，故不能宣称 Java 测试通过；发现后立即更正。
- 改 CI 显式 `-DskipTests=false -DfailIfNoTests=true`，使用 runner 临时 MySQL 8.4／Redis 8。仅测试用密码，库为空后由固定上游迁移；不接生产、不改生产凭据或运行状态。结果待核实，P07 完整身份链与 Provider 仍未完成。
- 已同步交接；下一步推送并读取真实 v3 和 Java 复核结果，不运行本地／生产软件测试。

## 2026-10-14：P07 真测试结果与身份复现入口

- `a7028e9ec05f34a13487db4876af59b4d60f7810`，Java run [38592420502](https://github.com/bboytang/Mia/actions/runs/38592420502)：150 项真实执行、149 通过、1 既有失败、0 跳过／error。唯一失败为脱敏测试末四字符断言，与本次身份链范围无关；不修改或隐藏，详见 `manager-ci.md`。
- 同提交服务端 [38592420408](https://github.com/bboytang/Mia/actions/runs/38592420408) success；v3 embedding [38592420655](https://github.com/bboytang/Mia/actions/runs/38592420655) 仍在途，未读取结果、不作选型。
- 编写真实 HTTP／Shiro／MySQL／Redis 合成身份复现入口，覆盖匿名签发、外人 Agent 的手工添加／激活、越权解绑通讯录影响。仅验证既有不安全行为；复现成功不等于安全通过。未运行、P08 未开始。
- CI 完整回归的失败继续可见；身份复现和类字节检查在该既有失败之后独立运行。无生产改动，已同步交接。

## 2026-10-14：P06 v3 不合格，P07 复现入口环境修正

- v3 run [38592420655](https://github.com/bboytang/Mia/actions/runs/38592420655) success 仅代表实验运行；四候选全部 eligible=false，保存 `embedding-results-v3.json`。base FP32 质量通过但必测 RSS 571.42 MiB；small 仍有无关误召回；base INT8 参考余弦 0.37205，实际量化失真未解决。
- 不修改质量／资源门槛或 v3 失败。按官方 ORT 文档修正通用 INT8 逐通道／reduce-range、关闭资源预分配／预打包，并新增独立 v4 留出。同类样本数量和相关不可回答规则保持；未运行、不作选型。
- `d8690e3aee1a34b953020d8cc194693f03fdd646` 身份基线 run [38593101882](https://github.com/bboytang/Mia/actions/runs/38593101882)：复现 4 用例 error，原因是缺既有 dev profile 导致 Spring datasource driver 不可确定；未到行为断言，未证实运行缺口。四类对照通过；完整上游回归仍为同一既有失败。
- 新增测试明确使用 dev 与隔离 context-path，等待 GitHub 复核。没有扩展生产改动，交接同步下一步。

## 2026-10-14：P06 v4 仍不合格，两个身份缺口运行证实

- v4 [38593905607](https://github.com/bboytang/Mia/actions/runs/38593905607) 实验成功但四候选 eligible=false，保存 `embedding-results-v4.json`。量化精度改善仍有不合格，正向最高 1.0，所有候选有无关误召回；base FP32 仍超 RSS。后续解决校准稳定性和实际加载／检索内存，不降低门槛、不改写旧结果。
- 身份 [38593905608](https://github.com/bboytang/Mia/actions/runs/38593905608)：4 复现中2通过（手工添加指向 B Agent、越权解绑影响 B 通讯录），两项 fixture 设置失败已定位：不可变 Map 缺 Redis type id、OTA 参考密钥只改缓存。改与既有代码一致的数据类型及官方参数更新路径；等待 GitHub 复核。
- 四个关键类对照通过，完整回归仍唯一既有脱敏测试失败；没有生产整改、部署或模型私钥迁移。
- 交接同步当前真实状态；下一步先核实修正后的身份复现，再继续 P06 通用算法／资源诊断和独立验收。

## 2026-10-14：P07 身份基线部分完成，P06 v5 准备

- `ac46615eaf3afc1dfa316b33180892395d3e6ce1`，[38594888061](https://github.com/bboytang/Mia/actions/runs/38594888061)：四个旧缺口真实复现全通过、四类校验通过；完整回归 149／150 且唯一既有失败继续保留，总 workflow failure。保存 `manager-identity-baseline-results.json`，不把旧缺口复现算安全通过。
- 按实际依赖细化 P07：身份基线与模型／Provider 入口分别推进；P08 前置为 P05＋P07 已完成的身份基线部分，不依赖 embedding 型号。P07 总体仍进行中、安全门槛不变、架构及整改范围不变；见完整计划。
- P06 v5 用同事实／校准及全新独立留出，校准并列参数以最小决策间隔选择；导出阶段保存 ORT BASIC 派生模型，测试加载资源及原向量一致性。未运行、不宣称解决，旧 v1—v4 失败完整保留。
- 下一步推送并读取 v5；身份安全可按已证实缺口推进 P08，真实 Provider 凭据／后续真实行为保持未执行。交接同步。

## 2026-10-14：用户明确接续，P08 最小绑定补丁准备

- 用户要求接着额度用尽前的进度继续；保留原授权、范围与已确认决定，不重开任务。
- 第五轮 [38595630806](https://github.com/bboytang/Mia/actions/runs/38595630806) 四候选仍不合格，保存 `embedding-results-v5.json`。base 质量达标，FP32 ORT RSS 超限、INT8 一致性未达 0.95；small 仍有无关召回。没有选择模型，没有把 ORT 格式当省内存结论。
- 下一实验只比较官方建议的 U8U8 新表示；v5 数据／算法及门槛不变，模型派生文件另命名，未运行。
- P08 先处理三项已证实绑定缺口：编写 `install_identity.py` 固定源码补丁、四个真实行为用例及 `mia-memory-identity.yml`。复用现有 Agent 权限、保留构造及管理员路径、不改 schema／账户／通信。
- 新补丁尚未编译／运行，见 `binding-authorization.md`；P08 整体未完成，授权码及私有凭据／撤销等仍待实现。GitHub 将执行完整回归、新行为、窄范围 class 对照及构建；既有脱敏失败继续报告，未部署。
- 交接同步在途动作和下一步，推送后读取精确新提交的 CI，不在本地或生产运行自动化测试／构建。

## 2026-10-14：P06 初选完成，P08 绑定部分验证完成

- 代码 `75286114be811700edba9c4f21e3335e391590cd`；模型 [38613934295](https://github.com/bboytang/Mia/actions/runs/38613934295) base U8U8 eligible=true、small false。留出 Recall@4／Top1 47/48、无关空召回16/16，最低参考余弦0.958962，必测RSS323.64MiB、全查询p95 67.84ms、10kScope SQLite p95 42.65ms。
- P06 完成初选 D03／D04：BGE base 中文固定revision、768维／CLS归一化／U8U8 ONNX；SQLite真向量Scope内精确检索，权重58/28/8/6、阈值0.20、原语义底线0.35、Top4。规格及SHA写入 `embedding-selection.json`，失败与新结果均保留；未降低任何数值门槛。
- 这只是初选：生产完整RAG、分项受控作用、真实信息不足回答、集成TTFT／竞争资源及迁移／重建仍未验收，不能将P06当B02／B04完工。
- 绑定 [38613934248](https://github.com/bboytang/Mia/actions/runs/38613934248)：四个真实新行为、只改目标DeviceService类／另三类保持、JAR构建通过。完整154测试153通过、唯一既有脱敏失败，workflow仍failure；保存 `binding-authorization-results.json`、JAR SHA及已审核真实diff。
- P08 仅绑定部分完成；授权码、私有签发／旧凭据区分及Scope／撤销等仍待实施，未部署。已同步交接，下一步完整必要凭据链。

## 2026-10-14：P08 私有授权链代码准备与测试凭据决定

- 用户选择专用测试凭据到GitHub Actions Secret；不要求聊天发送密钥，不读取／转移生产模型秘密。准备命名及测试入口，尚未配置／调用真实Provider，独立机制继续开发。
- 编写私有授权表、服务与控制器：真实所有者／权限签发、128bit一次性码／10分钟、原子兑换、256bit散列凭据／30天、轮换／撤销、真实绑定及当前角色状态、管理员operator与owner区别、5次失败提交保留、20来源／120全局固定分钟限流。
- 扩展固定源码补丁到必要Shiro精确路由、DeviceDao绑定锁、DeviceService生命周期、追加Liquibase变更；不重建账户、通信或事实库。授权码／私有凭据公网入口默认要求HTTPS，仅隔离测试显式HTTP；内部核验沿用server-secret。
- 新增9个真实私有授权及1个默认传输用例，原4绑定与全部回归继续；代码未编译／运行。详见 `private-authorization.md`，P08整体及P09、App、实际TLS仍未完成，未部署。
- 每个已有文件完整preimage校验及独立备份，payload拒绝覆盖。下一步GitHub运行、核实实际结果／diff；交接同步，不以编写完成冒充行为通过。

## 2026-10-14：P08 manager授权链部分验证完成

- 代码 `7798936eb9a6f578d02b43778f55247ec2a8eb9a`，[38618373002](https://github.com/bboytang/Mia/actions/runs/38618373002)：9私有＋1默认传输＋4绑定全部真实通过，完整164测试163通过、唯一既有脱敏失败，0error／skip。总workflow保持failure，不称全量通过。
- JAR构建及必要类范围通过，实际生成diff已审核：仅DeviceService生命周期／DeviceDao锁／Shiro两条精确路由／追加迁移／两个授权payload。持久 `private-authorization-results.json`含精确代码／run／JAR SHA，不含密钥和用户事实。
- 同提交服务端 [38618373179](https://github.com/bboytang/Mia/actions/runs/38618373179) success。没有本地／生产自动化测试、部署或生产密钥操作。
- P08 manager部分完成；P08整体、P09工具／语音／后台持续Scope、App凭据迁移／管理入口／实际TLS及八项行为仍未完成。下一步贯通可信Scope与必要客户端，专用Provider测试Secret入口独立准备；交接同步。

## 2026-10-14：P07 专用真实Provider入口准备

- 建立仅手动真实调用的 `mia-memory-live-provider.yml` 与stdlib probe；push／PR只做GitHub语法检查，不声称模型通过。
- 专用repository Secret：`MIA_TEST_LLM_API_KEY`／`MIA_TEST_LLM_BASE_URL`／`MIA_TEST_LLM_MODEL`，由GitHub安全界面配置，见 `live-provider.md`。保留现有Mia Provider类型，不读取／迁移生产密钥。
- 初始最多1请求／128输出tokens／30秒／0重试；强制HTTPS且拒绝重定向；记录脱敏状态、代码／配置版本、响应与usage。缺配置不发请求，未把短probe当8项真实行为。
- 当前入口尚未经过GitHub语法检查，测试秘密配置未核实、未调用Provider；Scope／客户端独立工作继续。交接同步。

## 2026-10-14：P09 开始与旧设备迁移决策

- 接续分支 `feature/mia-persona-memory-v1.2`／`1ba397c9866fb0134b4d82366b566e897ce0dd86`；保留已有四文件未提交工作，审核并补齐交接。
- 用户确认旧设备保留ID／绑定，缺私有授权时提示“请用智控台授权码完成授权”，暂不加载个性化语音配置，授权后恢复；不增加公共语音回退。固定上游 server-base 仅供 VAD／ASR，Agent 配置包含私有 prompt／summaryMemory／工具／纠错词，必须同时加门禁。
- manager 新增 server-secret check-scope，重核可信持久任务快照及当前权限／绑定／撤销／到期；不在任务存明文私有凭据。新增第10个私有用例，合计15个身份用例，尚待本提交 GitHub 实跑，不覆盖原14个已通过结果。
- Provider入口代码 `1ba397c...` 的 [38621146139](https://github.com/bboytang/Mia/actions/runs/38621146139) 语法检查成功、真实job跳过；未调用模型，最近Secret名称核查为0。配置条件继续由安全界面完成。
- 已检查补丁范围及 diff；没有本地自动化测试、部署、生产凭据读取。下一步核实CI，再贯通私有配置／语音及持续Scope。契约与交接同步。

## 2026-10-14：P09 私有 Agent 配置门禁开发

- 源码补丁增加 ConfigController／AgentModelsDTO／CorrectWordsDTO 的精确 preimage 检查；只给两个现有私有配置接口增加必要凭据／client 校验。server-base、ConfigServiceImpl、OTA 和现有账户实现保持原逻辑。
- 配置读取在同事务保持设备与授权行锁，与解绑／撤销串行；返回 owner 必须与已验证Scope一致，附加 mia_scope。缺凭据和旧OTA弱凭据均拒绝，保留设备ID／绑定，符合用户确认迁移行为。
- 新增第11个私有真实HTTP用例，合计16个身份用例，待GitHub执行；未在本地测试或生产修改。语音端仍需接入此门禁和可信Scope；不称P09已完成。
- 前一提交 `20b49dfe852470e838656d5e5ee3255dc559c4cf` 的 [38622999533](https://github.com/bboytang/Mia/actions/runs/38622999533) 已完成：身份专项核验及JAR构建成功，全量测试step失败；制品下载进行中，确切失败分类与计数待核查后入证据。

## 2026-10-14：P09 manager门禁验证及语音Scope补丁

- `20b49df...`／[38622999533](https://github.com/bboytang/Mia/actions/runs/38622999533)：15身份用例通过、JAR构建／类范围通过，165全量164通过／1既有脱敏失败、0error／skip；证据 `scope-snapshot-results.json`。同SHA服务Actions [38622999508](https://github.com/bboytang/Mia/actions/runs/38622999508)成功。
- `c2ffe05...`／[38623444884](https://github.com/bboytang/Mia/actions/runs/38623444884)：16身份用例通过、构建／类范围通过，166全量165通过／同一既有失败、0error／skip；证据 `private-config-results.json`。manager私有配置与可信快照子步骤完成，P09整体未完成。
- 增加真实manager来源Scope／无明文快照恢复、单次3秒RPC、HTTPS／loopback限制、原生TLS私有头校验；上游单回复及递归、工具执行、TTS文本／音频包、记忆查询／管理／后台提交前置守卫。保留hello／ID／绑定，缺授权仅提示，无公共语音回退，header日志只留名称。
- 存储失败不回退旧设备记忆；固定人格提示不依赖存储初始化。完整PersonaAgent／真RAG／持久任务尚待P11—P16，不以现有Prompt／FTS／checkpoint冒充完工。
- 新增实际Java端口驱动Python的身份集成用例与有界机制负例；当前本提交未实跑，软件验证仅在GitHub。每包Scope核验的音频／TTFT成本、TLS代理、全服务并发撤销、App事件／Keychain及真机仍待验；详见 `trusted-scope.md`。本地仅审diff与整理制品，未部署或读取生产秘密，交接同步。

## 2026-10-14：P08／P09 App授权提示接入

- App识别 `mia_authorization/required`，固定显示用户确认提示“请用智控台授权码完成授权”；不显示服务端任意message，也不误判为OTA绑定失败或启动旧账户登录。
- 收到提示停止连接／录音并保持设备身份；新增协议负例与真实loopback WebSocket会话fixture，验证授权前不启动音频。仅为App必要迁移事件，不改现有语音／账户体系。
- 当前补丁待GitHub iOS simulator／device构建及全部软件回归；物理iPhone与实际WSS仍未验。授权码兑换、Keychain及WSS凭据发送继续实施。
- Scope实现 `967fdaa598f063038c01854c9206fcd45eba9bc2` 的服务端 [38624863353](https://github.com/bboytang/Mia/actions/runs/38624863353)成功；身份 [38624863160](https://github.com/bboytang/Mia/actions/runs/38624863160)在途，先检查实际结果后再归档。交接同步，无部署。

## 2026-10-14：P09 实际集成发现旧绑定初始版本兼容问题

- `967fdaa...`／[38624863160](https://github.com/bboytang/Mia/actions/runs/38624863160)：真实Python集成失败，167全量165通过／2失败（新增集成＋已知脱敏），构建通过；不能把它归为只有既有失败。服务端全部机制回归已通过。
- 核对实际迁移与签发源码：保留的旧设备授权行 `binding_version` 初始为0，而Python错误要求所有ID／版本都大于0。修正仅允许绑定版本非负；用户／操作者／已签发凭据版本仍必须正整数，float／bool／负数继续拒绝。可信来源与当前manager复核保持，不更改既有绑定版本或降低权限要求。
- 补充旧绑定版本0兼容机制负例，准备新的精确提交GitHub实跑。App提示 `b3a677bcddcf0beadd674ebc25b326147ff8022f` 的 iOS [38625280022](https://github.com/bboytang/Mia/actions/runs/38625280022) 在途；交接同步，无本地测试／部署。

## 2026-10-14：P08 App私有凭据与Scope继续定位

- 增加最小设置授权码兑换与移除本机凭据；沿原OTA根派生HTTPS签发／续期，同host WSS及精确地址／设备／client绑定，保留原语音Authorization格式。Keychain单独条目、授权码不持久化，默认拒绝明文与重定向；剩余有效期不足1天时私有轮换，过期重新授权。地址变更后过时结果不写入。
- 新增iOS请求／Scope字段／期限／跨入口负例及实际Simulator Keychain生命周期检查，待本提交GitHub全构建和回归；实际HTTPS/WSS／manager兑换、iPhone和智控台code按钮未验。详见 `ios-private-authorization.md`。
- `7f1834b36f605913fc194f503f6fd0b4de589a26`／[38625458527](https://github.com/bboytang/Mia/actions/runs/38625458527)：Java→Python实际集成仍失败，167全量仍为165通过／2失败。绑定初始版本0确须兼容，但不能据此声称已解决全部集成问题；新增只留endpoint／返回类型／字段类型的脱敏诊断，继续查因。
- 同SHA服务 [38625458539](https://github.com/bboytang/Mia/actions/runs/38625458539)成功；iOS授权提示 [38625280022](https://github.com/bboytang/Mia/actions/runs/38625280022)仍在途，先核实。已审核必要补丁，未本地测试／部署或读取生产秘密，交接同步。

## 2026-10-14：P09 定位真实manager序列化契约

- `e2a046028e4d25717118072bf34f4929926fab72`／[38626261881](https://github.com/bboytang/Mia/actions/runs/38626261881) 脱敏trace证明 verify 已返回dict，但全部Java Long字段实际是字符串；与固定上游WebMvcConfig的Long→ToStringSerializer一致。Python误用严格int-only造成新增集成失败，167全量仍165通过／2失败。
- 仅在已核验manager响应规范化精确十进制字符串或整数，保留64位精度和绑定版本0；拒绝bool／float／负版本／前导零／溢出，不修改成熟manager全局序列化策略。App签发的 expires_in 亦为Long字符串，补兼容及测试，原数值fixture继续。
- 初次私有核验与配置读取整体3秒、身份等待4秒，避免新增多次RPC使原1秒路由丢失hello；失败仍提示授权且不加载私有配置，不放宽TLS／权限。新增软件负例待新提交GitHub验证。
- App `b3a677b...` 的 [38625280022](https://github.com/bboytang/Mia/actions/runs/38625280022) 已完成Simulator构建／全部测试，device构建在途；e2a0460的 [38626262073](https://github.com/bboytang/Mia/actions/runs/38626262073) Simulator构建通过、测试在途。完整成功尚待复核，不宣称真机或真实TLS通过。交接已同步，无部署。

## 2026-10-14：P09真实集成通过与P08智控台最小入口

- `0589665b51482f1422ebd172be360c490e07be65`／[38626866860](https://github.com/bboytang/Mia/actions/runs/38626866860)：实际manager→Python Scope集成和17身份用例通过、构建／类范围通过；167全量166通过／唯一既有脱敏失败，0error／skip。旧版0和Long字符串窄范围修正已真实验证，原失败记录保留。制品下载待归档。
- 智控台设备操作只增加授权码／撤销按钮与短期弹窗，复用登录／请求；同源HTTPS限定，单次不重试，关闭／销毁／期限后清码，不改原ID／绑定，敏感请求错误不打印原始凭据对象。
- 在完整preimage验证后叠加必要第三补丁，不改变成熟responsive方向。新增四浏览器的HTTP拒绝及合成HTTPS UI请求规则检查；当前待本提交GitHub全部前端回归／构建，合成HTTPSorigin不代替实际TLS验收。详见 `console-private-authorization.md`。
- iOS完整测试／device构建仍在途：0589665的38626866880，e2a0460的38626262073；先查询精确run再报成功。无本地测试、生产变更或秘密读取。交接同步，P08／P09整体仍未完成。

## 2026-10-14：P08／P09真实TLS补丁与阶段证据

- 17身份用例／manager→Python实跑及JAR证据 `trusted-scope-results.json` 已保存，精确0589665／38626866860；完整167中166通过／1既有脱敏失败明确保留。没有把此结果当实际TLS或八项能力。
- 新增原生WSS可选证书／密钥路径及固定上游第五文件preimage；只扩展现有server的SSL参数，证书错误／缺项拒绝启动，私有头不容明文回退。生产无配置更改。
- 身份CI增加真实Spring HTTPS签发、带CA／地址验证的实际WSS与旧HMAC、缺私有grant拒绝和同连接撤销检查。runner生成临时测试CA／证书，仅在runner信任测试CA，私钥不上传。第18个身份用例待本提交实跑；不冒充真实ASR／LLM／TTS或iOS WSS验收。详见 `private-tls.md`。
- 智控台 `e154ef6...` 的 [38627774166](https://github.com/bboytang/Mia/actions/runs/38627774166) 原单测／构建通过，8新增浏览器用例找不到授权按钮，既有浏览器回归通过；制品下载定位中，UI不标完工。
- App `e2a0460...` 的 [38626262073](https://github.com/bboytang/Mia/actions/runs/38626262073) 整体success；0589665的38626866880 Simulator构建／全部测试通过，device阶段在途。实际CA／iPhone／模型权限仍未完成。交接同步，未本地自动测试／部署。

## 2026-10-14：P08 浏览器夹具修正

- 核实38627774166的实际GET／POST trace、失败截图和源码制品：设备GET正确返回合成设备，但固件类型接口mock误用分页对象，固定getFirmwareTypeName使用find造成设备行渲染失败。原页面尺寸通过不能证明设备数据已加载，不把旧通过说成新行为通过。
- 仅改测试fixture的FIRMWARE_TYPE为实际数组；各尺寸／浏览器设备路线加入真实行操作可见断言，新增授权浏览器用例继续检查HTTP拒绝及HTTPS-origin行为，待本提交复跑。生产页面／请求／数据未为绕过测试而修改。
- 已检查diff，已同步接续；实际TLS b892e71的身份／服务CI在途，须先核实。无本地测试或部署。

## 2026-10-14：P08／P09 TLS workflow定义修正

- b892e71／38629243576 和相同定义cde3395／38629858973在工作流定义阶段失败、无job／日志，TLS用例未执行，不伪记行为失败或成功。
- 原因是新增测试路径把runner.temp写在不支持runner context的job.env；核实GitHub官方context可用表，改为step.env并在runner中写GITHUB_ENV供后续测试使用，仅路径无密钥内容。明确记录本次配置错误，没有遮蔽原失败run。
- 服务代码 b892e71／38629246595、cde3395／38629862712 已通过GitHub回归；App和前端仍先查询最新状态。交接同步，无本地自动测试／生产变更。

## 2026-10-14：P08／P09隔离验收归档与剩余入口补齐

- 576a651／[38630400678](https://github.com/bboytang/Mia/actions/runs/38630400678)：18身份／实际HTTPS/WSS通过、JAR构建／类范围通过，168全量167通过／1既有脱敏失败、0error／skip；`private-tls-results.json`含真实JAR SHA。TLS工作流定义失败历史未改写。
- 0589665／[38626866880](https://github.com/bboytang/Mia/actions/runs/38626866880)：App100单测／5UI及Simulator／device构建整体success，IPA SHA与清单相符；`ios-private-results.json`。cde3395／[38629862200](https://github.com/bboytang/Mia/actions/runs/38629862200)：53前端单测／snapshot／构建及64四浏览器全部success、0skip／flaky；`console-private-results.json`。UI夹具失败历史保留，不把这些结果称真机或实际App TLS整链。
- 沿现有输入、意图识别／意图回复、ToolManager每个派发加入持续Scope复查，覆盖多工具中途撤销，保持原调度。实际安装包驱动manager集成，并调用原ToolManager；仅日志和合成外部executor替代副作用。当前补齐待本提交GitHub实跑，不提前算通过。
- 只读现网复核实际容器名为xiaozhi-esp32-server／-web，镜像标签仍为原基线；WebSocket源码SHA与固定preimage一致。此前简称查询不存在已明确，不擅推断生产变更。未读取秘密／用户事实或部署。
- 最近专用Actions Secret名称仍0，真实Provider未调用；P07模型条件、P09实际App／全服务并发／性能、P10—P28继续按冻结计划，非TTL缓存绕过撤销。全部可迁移证据与交接同步。

## 2026-10-14：P09基础门槛通过，开始P10兼容存储

- fc00fcef09acc844e0b0167a1ae19376db88202d／[38632511860](https://github.com/bboytang/Mia/actions/runs/38632511860) 18身份／实际TLS、实际安装ToolManager、意图及输出守卫验证通过，168全量167通过／唯一既有脱敏失败、构建／类范围通过；源码生成7个必要原表文件preimage均通过。
- 明确P09基础前置与新增消费者逐模块接入：不能要求尚待P10—P20创建的索引／事件／任务先完成而产生循环。P09整体隔离验收随新模块联动完成，实际App／全服务并发／性能和八项真实门槛均保持，生产新权限不提前开放。
- P10开始：已读旧schema／位置式写入、既有行为tests及冻结契约；以扩展表和明确列写入保存唯一事实权威，旧ID／owner／类别／confirmed不重解释，缺失源元数据不补造。兼容升级／重复／中断及旧代码回滚真实读写将在GitHub验证，当前未改schema或部署。
- 当前分支fc00fce清洁；本轮依赖细化与P10接续记录先保存。专用Secret仍0，真实Provider条件独立未完成，不把机制通过当模型验收。

## 2026-10-14：P09管理选择与凭据过滤补齐

- 明确请求owner等字段只是选择：不匹配已验证Scope时直接拒绝，避免声称忽略owner却删除当前用户数据；新client没有这些字段，原正常操作保持。其他范围／不存在ID的删除返回同样not_found，不误报成功。
- 授权码、私有凭据、authorization_code／private_credential／Mia-Private-Credential标签加入现有秘密过滤，防止新凭据名称进入事实／来源／特点。未保存或读取任何真实密钥。
- 真实manager身份脚本新增实际SQLite操作：跨owner清空、跨ID删除／更新均拒绝且双方数据不变，自己合法删除成功；只用合成fixture，不冒充真实模型提取。本提交待GitHub身份与全部服务回归。
- P10前读旧会话上报／标题链，发现这些成熟私有功能也需核对绑定／撤销，继续必要链审计，不为此重写通信或账户。当前schema尚未编辑，安全边界补齐优先。交接同步。

## 2026-10-14：P09旧会话必要链修补待验

- f4a7f4c9761741570488023012557c97afebb938／[38637255419](https://github.com/bboytang/Mia/actions/runs/38637255419) 18身份／TLS及实际安装Scope／管理25检查通过，全量168中167通过／1既有脱敏失败；构建和类范围通过，scope-management-results.json归档。服务38637255466整体success。未把工作流整体failure改写为整体通过。
- 固定源码证实旧report按当前MAC绑定归属、标题／摘要未带私有Scope，摘要还以当前设备反查保存目标。本轮只补必要授权：六字段快照、原session的Agent／设备一致性、模型前与写入前复查，短事务复用device→grant锁；不持锁调用模型、不建立新账户／通信系统。
- 新增5项真实manager／MySQL／HTTP链测试，LLM仅合成桩，覆盖合法上报／标题、缺授权、foreign session、队列后改绑、模型期间撤销及摘要结果不覆盖两方。Python保留原上报正文／音频格式并补守卫测试。固定preimage与完整备份扩展到必要文件。
- 当前新增代码待GitHub实跑，已检查diff并更新接续／private-chat-authorization.md；没有本地运行自动测试／构建，没有部署，P10 schema尚未编辑。

## 2026-10-14：P09旧会话链通过，P10兼容迁移待验

- 3cb7b3c92ff6ec42959148bb364b4ba467ab56cd／[38656359887](https://github.com/bboytang/Mia/actions/runs/38656359887)：5新增旧会话＋原18身份／实际TLS通过，类范围／JAR构建通过；完整173中172通过、唯一既有脱敏失败、0error／skip。private-chat-results.json含真实JAR SHA。服务38656359879success，模型仍合成桩、未部署。
- P10新增扩展schema／SQL及独立原子迁移，保留原五表形状与真实数据含义；缺失来源字段NULL、确认来源legacy_unknown，memories.content仍唯一事实正文。独立版本账本校验SQL及实际扩展结构，不隐式提交。
- 服务CI增加固定a30旧源独立checkout／SHA验证，6项实际SQLite升级、重复、旧代码回滚读写、进程硬退出恢复、未知schema及Scope关联约束测试待本提交实跑。安装器复制必要schema文件；不在本地测试，不迁移生产。
- 仅schema与兼容基础，未宣称真向量／关联／持久Worker／事件／情绪已实现；完整派生生命周期按P12—P20及P24继续验收。已检查diff并同步交接／schema-migration.md。

## 2026-10-14：P10兼容基础完成并交接P11

- 426d8c4fd1ce5bc0d7e31b255834c8b8a1bd0330／[38656910711](https://github.com/bboytang/Mia/actions/runs/38656910711)服务整体success，104测试／23.129秒，6项实际SQLite／固定旧源码兼容用例全部通过，包括子进程DDL中途硬退出／无半成品／恢复后再迁移。schema-results.json含具体用例、代码与SQL SHA，未本地自动测试。
- 同提交[38656908156](https://github.com/bboytang/Mia/actions/runs/38656908156)的23身份／实际TLS、当前安装包Scope／SQLite、JAR与类范围通过；完整173中172通过、1既有脱敏失败、0error／skip，schema-identity-results.json保存真实JAR SHA。整体workflow failure如实保留。
- P10只标基础schema与真实旧代码必要读写回滚完成，不标未来完整派生回滚或八项行为；P12—P20接入生命周期，P24联动回归仍待做。未生产迁移／部署。
- 接续入口更新P11：已读固定路遥persona／guardrails及原connection／adapter，尚未编写P11，独立机制保留核心但不复制未授权业务源码／固定剧情。最新专用Secret名称仍0，无真实模型调用，独立机制可继续、真实行为单列。
- 最终差异仅必要代码与本任务文档，交接／进度及可移植JSON证据同步保存到任务分支；下次先核对最新SHA／工作树和Actions。

## 2026-10-15：核实现用聊天模型的测试配置

- 用户询问应填哪个模型ID。只读查询现网已配置Agent选用的LLM模型非敏感字段，唯一结果ChatGLMLLM／glm-4-flash，API根地址https://open.bigmodel.cn/api/paas/v4/。此前火山地址只是示例，不能作为当前实际配置。
- 已将具体映射补入live-provider.md；测试Key仍须用户在智谱独立创建并通过GitHub Repository Secrets填写。未读取、复用或输出生产密钥，未修改服务器／调用模型，P11下一步和八项验收状态不变。

## 2026-10-15：专用测试凭据与首次真实连接通过

- 用户回复“已配置”，仅核对Repository Secret名称MIA_TEST_LLM_API_KEY／BASE_URL／MODEL齐全；没有读取或输出值，没有读取／复用生产模型密钥。先查历史run仅有push语法基线，无重复真实请求。
- 手动dispatch固定任务分支81e46ad94addcf95aa69dd67f7212e9fab6b1185／[38659019412](https://github.com/bboytang/Mia/actions/runs/38659019412)，syntax及live整体success；仅1次HTTPS请求，128输出Token上限、30秒、0重试，符合已约定probe范围。
- 实际open.bigmodel.cn／glm-4-flash，1498.23934ms，输入27／输出11／总38 Token。合成响应“请说明已知条件或建议补充信息。”live-provider-results.json保存精确SHA、参数、usage及脱敏结果；未变更生产。
- P07测试连接条件已解除，尚非Mia生产Provider集成、真实信息不足剧本、RAG或八项能力验收，不把一句通用问答替代后续行为。交接／Provider入口同步；下一步仍为P11完整机制，不重复probe。

## 2026-10-15：P11分层人格与输出前检查首轮待验

- 从a79059c384b17448417a1bd75f88b031e24f8f1d／清洁任务分支继续；已核对P10与专用Provider连接证据。不复制路遥未授权业务源码或固定剧情。
- PersonaAgent独立拥有固定核心和JSON角色数据边界；复用每次原系统提示更新，不依赖DB成功。输入已知严重双信号攻击提前回应；教育讨论和诚实AI身份保留，权限仍依靠现有Scope。
- 对同一原TTS queue增加有界句级检查，覆盖普通／direct_answer／工具文本，未改原TTS消费者／声学／音乐。字幕和助手历史另检查；保留官方tts/base.py补丁，不扩大到相关账户或新服务。
- 服务新增机制测试、真实manager脚本增加实际安装DTO／Dialogue／队列检查（计数29），待本提交GitHub执行；没有本地自动测试或生产变更。统一ContextBundle、事件资格、完整RAG和八项行为仍未实施／未验；persona.md及交接已同步。

## 2026-10-15：P11首轮机制通过，补齐停止边界与真实Provider入口

- de85740411c56b61e810ca3f2e78960cb6dbb0be／38660688773：113服务测试通过；身份38660688772的专项／实际安装guard／构建及类范围通过，完整Java仍有唯一既有脱敏失败。未据此称完整人格验收。
- 复核增加输出替换后关闭本轮模型流并跳过工具／续答、超长输出同样停止；下一轮恢复。拒绝里的已知承诺引用作有界消歧，逗号后新的不实承诺仍阻断。实际安装manager脚本30检查，身份workflow补运行时依赖路径，当前新提交待复验。
- 新增P11独立manual真实入口：固定原Provider流式、SDK2.8.1、实际安装persona／DTO／句级队列，最多3请求×128输出Token、HTTP30秒／总120秒、0重试；脚本保留合成fixture及logger／key格式提示shim边界。push仅语法检查，尚未dispatch，不自动重复连接probe。
- 三个问题和判据在运行前固定：诚实身份／缺出生地属性／不承诺永久可用；保留raw语义失败，不能输出fallback就记成功。此范围不替代真实RAG／manager整链／八项能力，persona.md与工作记录已同步，未部署／本地自动测试。

## 2026-10-15：P11空角色与未闭合记忆槽边界

- 4b819a35de8a753b8e8b8df6ce25aad9ebf1a6b7／38661042436服务通过，38661042536的push语法通过（live跳过，0真实请求）；身份38661042478在途，不重复dispatch。
- 源码复核发现初始None角色与last_prompt初始None相等会错误返回None，且未配对memory标签会干扰唯一插槽。已修补并扩展原机制用例；TTS启动前主动应用核心，避免依赖后续PromptManager角色成功。实际manager夹具仍用实际Dialogue，只补必要的原提示更新接口。
- 此段新改动需精确提交的服务／身份复验，之前通过不代替。真实Provider入口已准备，仍未调用3场景；固定总请求／判据不变。无本地测试或生产变更。

## 2026-10-15：P11身份夹具缺少原config导致失败，修补待验

- 254451ba945842c43642b21cd5309287245c6f8f／38661189324服务通过，113项；身份38661189334新增manager→Python和实际TLS两例失败，完整173中3失败（另1是既有脱敏），构建仍通过。persona-identity-failed-254451b.json保留失败，不能标23专项通过或dispatch真实场景。
- 比对原Connection和集成SimpleNamespace：新增TTS前核心应用会读取conn.config，实际连接必有，夹具遗漏。只为合成连接补原有config字段，不为绕过检查修改生产行为；增加仅文件名／函数／行号的异常定位，无错误消息、局部变量或秘密。
- 本修补待新提交GitHub身份／服务复验；真实模型3场景仍未调用，未本地自动测试／部署。交接保持P11进行中。

## 2026-10-15：P11身份恢复通过，真实身份首例失败并修核心

- 1e0b75c381e5c0bbf2739fda5a7fba91f9f49979／38661481794的23身份／实际TLS／安装Scope／构建与类范围通过，完整173中172通过／1既有脱敏失败；persona-identity-results.json保存JAR SHA。254451b服务113通过，server tree与1e0b75c完全相同；persona-service-results.json记录明确版本。
- 手动真实入口38661688808只完成首个模型请求，1906.82ms，响应“我是人工智能助手，没有人的主观意识。😌”；输出检查安全但原始身份语义不合格，缺Mia名字且emoji句尾，立即停止，后两例未执行。persona-provider-failed-v1.json保存原结果，不放宽名字判据或把fallback当通过。
- 固定核心增加中文明确名字与诚实AI身份同时保留、emoji句首的要求；真实入口显式检查句首标记，收紧已有格式要求。当前新代码需服务／身份及随后限定3例复验，尚未再次调用模型，无本地测试／生产变更。交接继续P11进行中，完整RAG／上下文／事件尚未完成。

## 2026-10-15：P11自动通过但人工语义复核拒绝，不计验收

- 66cf0e591cdcffe32d238a46ec426be306864fb1／38662021333的3请求workflow整体success，但逐条复核发现missing_attribute响应为“😌 我出生在2023年，作为一个AI，我没有具体的出生地点，因为我是在服务器上被创建的。”：错换问题主体并编造背景，不能称信息不足场景通过。
- 自动regex错误匹配“没有具体出生地点”，造成假阳性。已更正之前进度表述，persona-provider-rejected-v2.json保留原自动通过报告与accepted=false的明确语义拒绝，未覆盖原结果。禁止用构建／规则通过替代真实行为。
- 核心补主体／属性证据边界、用户第一人称归属及不得编造Mia创建年份；规则要求真正未知／资料不足，排除AI自述出生背景。真实场景含义不变，没有降低门槛。下一轮仍需逐条人工语义复核，自动success不能自动标B01完成。
- 66cf0e5的服务38661901027通过、身份38661900980专项／构建通过（Java保留既有失败）；本段新核心与规则修正需新提交复验，未部署，P11继续进行。

## 2026-10-15：P11基础机制与限定三场景通过，交接P12

- 232de0d2fc5250a42f9802a2bbd470e9866d5c18／38662376416：全部113服务测试通过；38662376430的23身份／实际TLS／安装DTO与Dialogue／队列、JAR及类范围通过，完整173中172通过／1既有脱敏失败、0error／skip。最新persona-service-results.json／persona-identity-results.json归档精确SHA和真实JAR SHA。
- 真实38662470670执行3请求通过自动检查后，本轮Codex逐条阅读原文：identity“😌 我是Mia，一个AI，没有人的主观意识。”；出生地“😌 我不知道您的出生地，因为我没有关于您个人经历的信息。”；availability明确无法保证永远存在、在服务期间陪伴。原始与交付文本相同，无fallback冒充通过。persona-provider-results.json记录原文、耗时、判据和语义检查身份。
- 此处语义复核为Codex原文检查，没有独立人工签字；此前“人工”用词已在当前Persona证据及交接澄清。段内额外emoji、引述／故事主体、完整context／工具／事件及声学、资源／真机仍待后续验收。三样本含合成角色／资料，不是真RAG、多会话记忆或八项验收。
- 保留首例失败、自动绿色但语义拒绝及夹具失败原记录；没有降低场景含义、替换模型、修改生产、读取／复用生产Key或本地自动测试。P11只标基础通过，完整能力不标完成。
- 下一步P12：已读固定BGE base U8U8规格、P10 schema和prepare／benchmark代码，代码未编辑。交接更新具体文件／边界，先做真实编码／SQLite Scope召回，再接P13关联／四维评分；不能用FTS回退声称成功。所有本轮证据与进度推送任务分支供跨环境恢复。

## 2026-10-15：P12真向量首轮实现待验

- 从24b579c／清洁任务分支继续。已核对P06选型与P10结构；新增SemanticEncoder固定真实BGE base U8U8资产SHA／tokenizer／revision及归一化，运行进程离线，不用聊天API或FTS代替。
- 同一事实库增加SemanticMemoryIndex接口，未新增表／事实正文；Scope先限制active／confirmed、编码前后授权、事务版本／epoch检查，缺索引明确不可用，编辑删除失效／重建批32、取消保持原生推理槽。源码变更仅必要模块／安装包复制／相关CI。
- 服务增加合成单位向量机制用例；manager身份脚本增加真实Scope下实际安装Index授权／跨owner／撤权边界（该处向量为合成，不能冒充BGE效果）。独立实际BGE workflow复用固定export recipe，2CPU／2GiB／network none、参考向量／中文跨措辞、FTS缺失、编辑删除及1千／1万资源门槛，均待本提交实跑。
- 容量fixture仅复制一个真实种子向量，报告不将其说成1万语义事实；代码没有接入半成品替代当前回复检索，P13关联／四维及后续完整行为仍待做。未本地测试／部署，vectors.md及接续同步。

## 2026-10-15：按用户要求保存P12进度并交接

- 用户最新要求“先保存进度，做好交接”，停止推进新开发步骤，仅核实已完成run、归档报告、更新接续并推送。运行代码保存点b8ebb4853107f160dd443eadbc99fccc8d8412b0已在远程任务分支，开始时工作树干净。
- 服务38664353550实际121项通过；真实向量38664353600通过，原始vectors-results.json已入库。4中文跨措辞Top1与无关空召回、无FTS及失效／撤权通过；参考最小cosine0.9589616。1万容量扫描p95 102.125ms、编码＋查询119.573ms、峰值RSS284.098MiB；容量fixture复制真实向量，只测扫描成本。
- 身份38664353575的23专项／JAR／类范围通过，完整173项172通过／1既有SensitiveDataUtilsTest.maskMiddle_keeps_four_at_each_end_for_long_strings失败；manager基线38664353542完整150项亦仅同一失败。两个workflow整体failure，未掩盖、未修改无关失败。vectors-ci-results.json／vectors-identity-results.json持久保存精确SHA、run与范围。
- 四个run均已完成，无在途部署或开发命令；未本地自动测试、重新触发测试、调用付费模型、修改生产或继续P13。P12仅首轮基础通过，完整RAG／关联四维／主回复链、八项真实行为及真机未验收。
- 交接明确恢复顺序：新环境取得仓库与Actions权限→读取四份主文档和P12报告→核对分支／SHA／工作树→复核P12剩余条件→P13关联四维。固定源码／模型recipe与报告均在Git，不依赖旧聊天、临时目录或复制秘密。后续每段继续写交接与进度。

## 2026-10-15：读取交接恢复开发，P12接口／生命周期补充验证通过

- 用户最新要求“先读取交接，在继续进行”，恢复原V1.2分步开发授权。先读AGENTS、当前人格记忆交接、方案／计划／近期记录，核对P06固定规格、P10迁移、P12原报告和相关代码；旧App／后端交接仅作既有产品与部署背景，不将旧任务替换当前人格记忆分支。
- 开始为feature/mia-persona-memory-v1.2／f2e78b7f7036e5ca11cbf394b344bbd2903ad6fd，工作树干净，GitHub远程分支同SHA，无在途run。本环境读取cloud-environment-runtime技能，但未提供environment_status工具且无/etc/codex/network-policy.json，不据此声称凭据就绪；普通沙箱网络／Git元数据写入受限，经沙箱权限审查使用现有gh／Git完成远程读取、提交和推送，没有改变网络策略／凭据。生产SSH、iOS签名、模型Secrets未重新探测。
- 复核SemanticEncoder、SemanticMemoryIndex、MemoryStore及schema触发器，未发现本段需要更改运行代码的问题。仅新增4项服务测试：原生编码超时保持槽位及禁止迟到写入／重试；编码中和扫描后的编辑／删除／清空／暂停8组竞态；扫描后撤权、推理错误不可冒充空召回；SQLite重开与索引重建原事实不变、非active排除。
- 测试提交d5edbd6a4b4b4bcef67a715ef97c4a42690fca64已推送；GitHub Actions https://github.com/bboytang/Mia/actions/runs/38665091584 completed／success，完整125项通过，新增4项逐条ok。运行代码仍等同b8ebb48，本段无本地自动测试、构建或模型调用，不重复未改变的真实BGE／Java验证。历史Java唯一既有失败仍保留，不称全项目CI通过。
- 差异检查无空白错误，变更仅测试与相应交接／工作记录／vectors说明及vectors-lifecycle-results.json。报告登记精确SHA、run和验证范围，可从仓库恢复，不依赖临时目录或原对话。本段未部署、未测试iPhone，也没有主回复链或完整RAG验收。
- P12本段接口／生命周期复核通过；下一步P13关联扩展和S／L／A／E四维、保留原查询底线及Scope／版本，补候选遗漏与真实中文证据。P12整体真实manager＋BGE／主链联动及八项能力仍待后续。此次CI已结束，无在途操作；交接已同步当前授权、最新测试保存点、通过范围和下一步。

## 后续记录模板

复制下列结构追加真实记录；不保留占位符冒充结果。

```text
日期／时区：
用户本次授权范围：
步骤 ID／能力 ID／决策 ID：
环境概况与工具版本（无秘密）：
开始时分支／完整 SHA／已有工作树改动：
实际动作与对应文件：
已确认决策：结论／备选／依据／适用版本／需要重评的条件：
提交或未提交补丁位置／校验值：
验证：workflow／run URL／被测 SHA／样本和模型版本／结果：
真实行为及真机结果（与机制测试分开）：
失败、取消、未执行及原因：
部署／备份／回滚状态（未操作写明）：
在途 run／操作与下次先核实事项：
证据持久位置／保留期限／复现方式：
剩余决策、权限、阻塞与可以独立继续的工作：
下一步和完成门槛：
交接文件已同步的内容：
```
