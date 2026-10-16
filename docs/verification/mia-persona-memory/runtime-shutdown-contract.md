# 实际服务关闭验证入口（2026-10-17）

此入口尚未通过真实CI；测试代码或本地受控测试不能代替实测。

当前实际句柄：bb230a00/[38973884791](https://github.com/bboytang/Mia/actions/runs/38973884791)，单次queued，等待终态。此前d106a686/38973027072在导出准备失败，完整保留shutdown-first-preparation-*；模型及实际生命周期阶段未执行。

`shutdown`套件复用既有真实manager测试用户、授权、Provider、BGE与SQLite，直接导入安装后的完整ConnectionHandler和app模块。执行原app.main、WebSocketServer、SimpleHttpServer、GC及同一持久Worker；实际Unix SIGTERM触发原关闭接线。另设TLS/WSS文本驱动，省略连接音频初始化及音频消费者，因此不证明音频/真机关闭或P23资源指标。

配置仅从CI环境中的测试manager地址和凭据进入原配置缓存；不用生产配置文件，也不以fake config.logger/util模块替代完整导入。日志使用真实logger，关闭携带异常局部变量的输出；原Provider请求/响应元数据仍按既有脱敏报告观察。stdin使用实际管道和原aioconsole监控。通过监听探测确认实际WS/HTTP已启动，进程退出后确认原端口关闭。

三个冻结合成用户分别执行：真实回复完成事件入队；原模型提案通过原validator后在原NativeLane受控保持；SIGTERM后1秒释放，原Worker在原预算内提交；新PID召回。第二个真实提案校验后保持至45秒（不制造输出/事实/任务），在关闭预算内退出且任务仍持久未提交；第三个PID由原Worker恢复，原尝试总数不超过2，唯一两事实/两向量及SQLite完整性核对。原任务120秒期限、30秒模型调用、两次提取上限、总进程关闭20秒都不放宽。

## 安装范围与依赖

仅临时Ubuntu GitHub runner的`shutdown`任务安装，不改变Windows虚拟环境、生产或其他套件。系统包：Ubuntu runner仓库的libopus0、libsndfile1、ffmpeg，实际版本由运行环境决定。CPU torch/torchaudio固定2.2.2，从PyTorch CPU索引安装；完整导入使用固定公开上游87c6df77b0220ddbd8fc804f984f83f69f3225e5的[requirements.txt](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/87c6df77b0220ddbd8fc804f984f83f69f3225e5/main/xiaozhi-server/requirements.txt)。其直接约束如下：

```text
torch==2.2.2
torchaudio==2.2.2
numpy==1.26.4
websockets==14.2
pyyml==0.0.2
silero_vad==6.2.1
opuslib_next==1.1.5
pydub==0.25.1
funasr==1.2.7
openai==2.8.1
google-generativeai==0.8.5
edge_tts==7.2.6
httpx==0.28.1
aiohttp==3.13.2
aiohttp_cors==0.8.1
ormsgpack==1.12.0
ruamel.yaml==0.18.16
loguru==0.7.3
requests==2.32.5
cozepy==0.20.0
mem0ai==1.0.0
powermem>=0.3.1
bs4==0.0.2
modelscope==1.39.1
sherpa_onnx==1.12.29
mcp==1.22.0
cnlunar==0.2.0
PySocks==1.7.1
dashscope==1.25.2
baidu-aip==4.16.13
aioconsole==0.8.2
markitdown==0.1.3
mcp-proxy==0.10.0
PyJWT==2.10.1
psutil==7.1.3
portalocker==3.2.0
Jinja2==3.1.6
vosk==0.3.45
```

沿用既有BGE制备依赖transformers4.51.3、onnx1.17.0、onnxruntime1.23.2、tokenizers0.21.1、safetensors0.5.3及固定BGE资产；本套件的服务运行Python保留torch2.2.2，导出器版本见后述隔离修复。powermem及传递依赖尚非完整锁定，`pip freeze`保留实际解析版本；这是全导入验证的依赖记录，不能宣称P24可重现安装已完成。没有启用第二套记忆或人格服务，选用模块为空以省略音频初始化；Mia仍只用原Worker和事实库。

首轮38973027072在BGE制备失败：torch2.2.2的onnx.export不接受既有脚本的dynamo参数。后续仅在临时runner另建导出venv，安装原导出器CPU torch2.6.0及上列固定BGE制备依赖；完整服务所在Python仍为torch/torchaudio2.2.2。两份pip freeze分别保存，既有导出脚本、模型版本、ONNX哈希要求不改，不用较旧导出器的不同资产绕过校验。本机和生产均不安装或更新。

失败时保留原报告、代码SHA、SDK片段、SQL与实际依赖；没有实际import/监听/信号/退出/恢复证据便不报告完整生命周期通过。
