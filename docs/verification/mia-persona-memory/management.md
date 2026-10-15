# P21 必要管理与兼容

状态：实现与GitHub验证进行中。仍使用原“记忆与成长”页面、现有WebSocket连接和mia_memory的request_id／action，不新增聊天页、管理站点或端口。

list／personality及旧事实操作的result继续保留memories／paused／personality，新增可选management={version:1,actions:[…]}。旧客户端忽略未知字段；新客户端缺失能力声明时只提供原操作。事件返回最多100条既有有界双方互动片段、状态及版本；片段来自既有来源表，删除来源仍清片段，不新增聊天历史保存。

新页面提供事件查看／删除，长期心情的明确启用确认、停用、分来源趋势、观察原句／时间／置信度／版本、更正／删除与清空。启用说明默认关闭、30日分析／90日保留和可能向云模型传递；停用已有观察可看，但不聚合或用于回复；清空观察不等于关闭授权。原“清空全部记忆与成长”继续清事件和观察。资格五观察／三会话／跨七自然日不变，真实跨日验收按用户决定自行测试。

客户端沿用单在途管理操作、UUID关联、8秒超时、取消／断连恢复和无录音连接，增加类型化result解码。mia_memory_job仅表示接收状态；显示“已接收，正在整理，尚未确认保存”，刷新通过同owner job_status读取终态；可省略id读取最新一项、无任务返回none，显式id继续兼容，重连不会丢失服务端状态，committed且confirmation_required明确显示待确认，而非提前称已保存。已取消／失败／有效空结果分开显示；晚到的旧任务状态不覆盖更新的任务。

测试范围：Python实际MemoryStore及adapter；真实manager TLS／WSS的能力声明／双方片段／停用原观察及越权拒绝；Swift旧快照／任务状态与同连接扩展操作／取消／无录音；模拟器既有页面的明确授权UI。客户端loopback为显式合成协议夹具，manager整链另测，未冒称实际App→真实manager→BGE→Provider整链。软件检查仅GitHub；真机、声学、完整真实行为和资源分别留P22—P25，未部署。

当前证据：[management-ci-results.json](management-ci-results.json)。后端22de963服务229、实际BGE／manager均通过，probe5dfa89a的实际身份38815615902通过。两轮probe错误（变量遮蔽／ID与admission字典比较）保留；运行权限未放宽。iOS当前4d4b5cc的38815987680待结果，P21不标完成；旧两个iOS run取消，旧22de963仍在途。当前客户端额外区分观察依据失效，不显示其更正入口。
