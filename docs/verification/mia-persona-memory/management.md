# P21 必要管理与兼容

状态：必要实现与GitHub验证完成，真机与完整真实行为另验。仍使用原“记忆与成长”页面、现有WebSocket连接和mia_memory的request_id／action，不新增聊天页、管理站点或端口。

list／personality及旧事实操作的result继续保留memories／paused／personality，新增可选management={version:1,actions:[…]}。旧客户端忽略未知字段；新客户端缺失能力声明时只提供原操作。事件返回最多100条既有有界双方互动片段、状态及版本；片段来自既有来源表，删除来源仍清片段，不新增聊天历史保存。

新页面提供事件查看／删除，长期心情的明确启用确认、停用、分来源趋势、观察原句／时间／置信度／版本、更正／删除与清空。启用说明默认关闭、30日分析／90日保留和可能向云模型传递；停用已有观察可看，但不聚合或用于回复；清空观察不等于关闭授权。原“清空全部记忆与成长”继续清事件和观察。资格五观察／三会话／跨七自然日不变，真实跨日验收按用户决定自行测试。

客户端沿用单在途管理操作、UUID关联、8秒超时、取消／断连恢复和无录音连接，增加类型化result解码。mia_memory_job仅表示接收状态；显示“已接收，正在整理，尚未确认保存”，刷新通过同owner job_status读取终态；可省略id读取最新一项、无任务返回none，显式id继续兼容，重连不会丢失服务端状态，committed且confirmation_required明确显示待确认，而非提前称已保存。已取消／失败／有效空结果分开显示；晚到的旧任务状态不覆盖更新的任务。

测试范围：Python实际MemoryStore及adapter；真实manager TLS／WSS的能力声明／双方片段／停用原观察及越权拒绝；Swift旧快照／任务状态与同连接扩展操作／取消／无录音；模拟器既有页面的明确授权UI。客户端loopback为显式合成协议夹具，manager整链另测，未冒称实际App→真实manager→BGE→Provider整链。软件检查仅GitHub；真机、声学、完整真实行为和资源分别留P22—P25，未部署。

当前证据：[management-ci-results.json](management-ci-results.json)。后端22de963服务229、实际BGE／manager均通过，probe5dfa89a的实际身份38815615902通过。两轮probe错误（变量遮蔽／ID与admission字典比较）保留，运行权限未放宽。

页面验证：22de963／4d4b5cc均102单测通过、新增UI失败。定向38816799405的AX证明入口只有2.3px露出，测试依据isHittable误停滚动；已撤回未证实的产品导航修改。3550c05的38818850351整行可见修正使导航及默认关闭通过，但点击开关未出现启用确认。47bcdc3把四个confirmationDialog统一为一个明确操作状态，保持授权说明与四项原操作，全量38820330282仍在途。原AX／截图制品保留，新workflow导出便携附件便于检查；未提前称修复或P21完成。见[原AX](management-navigation-ax.txt)、[诊断与制品](management-navigation-diagnostic.json)。

最新38820330282终态失败但102单测通过。原截图已实际查看，AX和合成触摸plist证明点击x201落在文字，原生开关在x313..364，未真正切换。撤回未证实的四dialog冲突重构，运行源码恢复4d4b5cc；仅测试改点内层原生开关。新全量结果待CI，仍不标P21完成。便携附件导出实际通过；见management-consent-hit-diagnostic.json及原PNG／AX。

最终P21结果：87d2427的[38821633956](https://github.com/bboytang/Mia/actions/runs/38821633956)success，102单测、6UI、模拟器与未签名设备构建通过。启用截图已实际查看并保存management-consent-enabled.png，原始完整日志无损归档management-ios-success.log.gz。历史失败不删除；本页先前在途描述为历史状态。后续路遥人格／整链变更另做回归，不将合成页面结果冒称真机或真实App→manager整链。
