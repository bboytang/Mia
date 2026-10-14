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
