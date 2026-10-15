# P22 真实联动验收

状态：准备中，P21客户端UI仍未通过，不能提前标P22完成；未执行真实模型请求。用户接管真实跨日验收的决定持续有效，其他冻结门槛不变。

第一项composed gate把前面分别验证的真实manager HTTPS授权／工作模型读取、实际SDK Provider、固定BGE编码与SQLite，以及原reply／completed_chat／MemoryWorker组合到同一隔离WSS服务。Java创建三个独立合成用户／Agent／设备，以真实授权码兑换私有凭据；选中模型来自现有GitHub专用测试配置，经manager可信Scope返回，客户端不能选模型或传API Key。仅测试临时MySQL保存该专用配置，原配置和密钥不进入报告；不读／改生产。

新冻结p22-integration-v1语料包含三组不同的普通用户输入及不同措辞追问，不复用之前的蓝色样本，不把预置事实或固定回复作为来源。每个合成用户源对话后，经实际完成钩子接收任务、原start_worker／stop_worker持久后台调度、同一Provider提取、实际BGE及事务写入；真实不同WSS会话召回并激活事件，终止并等待服务进程退出后重启，再三个后续会话验证重复幂等／删除来源后未知与事件失效。每组最多18次实际请求／768输出、HTTP30秒、SDK无重试，Worker保留既有最多两次提取总尝试，三组最多54次；通常六次聊天＋各自提取共12次／组，模型／提取异常的实际尝试仍计入18次上限。每组外层300秒，工作流35分钟上限；第一次只准备入口，P21通过后再dispatch。

报告保存实际请求、原文／投递结果、ContextBundle输入与诊断、来源／任务终态、Session与PID、代码／语料hash；模型配置／密钥与私有凭据不入报告。原始失败不改写，自动命中只是检查，仍需逐条读原回答。

范围边界：WSS驱动原安装reply／completion桥，实际使用manager、Provider、BGE／SQLite；测试只省略麦克风／TTS消费者，不宣称声学或真机。第一项gate重点验证B02／B05的首次整合，不把其成功替代全套B01—B08：B01特点成长／注入、B03所有结束路径及持久故障、B04完整留出四维、B06完整隔离矩阵、B08十续答场景×三次仍须扩充。原ConnectionHandler整服务集成范围亦须核对，不将测试驱动连接视作完整服务验收。B07真实跨日用户自测。小请求测试包络不解除旧模型别名生产容量限制；官方GLM-4文档现以日期版型号描述，不能直接推定旧别名同容量（https://docs.bigmodel.cn/cn/guide/models/text/glm-4）。P23不得用此处无限制runner结果代替2核2GiB性能，P24仍须已安装补丁升级及旧版本读写回滚。

准备入口最新源码806fdd9的[38821133535](https://github.com/bboytang/Mia/actions/runs/38821133535)仅Python／JSON语法成功；真实组合job在push上skipped。Java编译、实际模型／BGE／manager组合尚未执行，计数0，不将绿色workflow称真实验收。源码hash及缺项见[behavior-ci-results.json](behavior-ci-results.json)。

准备入口进一步改用安装后的ConnectionHandler.chat完整方法与原装饰器，不自写chat替代。沿用verify_mia_reply已有AST加载方式，只省略音频／插件导入；构造时仍绕过音频初始化，不称完整WebSocketServer生命周期验收。通过原change_system_prompt、begin_turn／reply／checkpoint／completed_chat，记录安装文件hash、实际Provider原文、最终历史及GuardedTTSQueue中的待投递文字；召回和删除后未知同时检查实际TTS文字。真实组合尚未dispatch，具体来源／正向路径待GitHub验证，不以此代码调整直接标原服务整体验收。
