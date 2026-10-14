# P10：兼容 schema 与原子迁移

状态：426d8c4fd1ce5bc0d7e31b255834c8b8a1bd0330／[服务CI 38656910711](https://github.com/bboytang/Mia/actions/runs/38656910711) 的6项兼容迁移及全部104服务测试通过；[身份CI 38656908156](https://github.com/bboytang/Mia/actions/runs/38656908156) 的23身份／实际TLS及构建、类范围通过，全量173中172通过／1既有脱敏失败。[迁移报告](schema-results.json)及[身份报告](schema-identity-results.json)已归档。未执行生产迁移，不据表存在认定 RAG／Worker／事件／趋势已实现。

## 唯一事实与兼容

原 owners／memories／sources／traits／checkpoints 的列顺序、ID、owner、类别、内容、时间与 confirmed 均保留。memories.content 继续是唯一事实正文；扩展表不复制正文，来源不伪造 Turn／Message／观察时间。旧 confirmed=1 只映射可用状态，confirmation_origin='legacy_unknown'，不声称用户主动确认。既有FTS暂留供旧实现兼容，仍不是V1.2完整RAG。

新增必要结构：事实内容／证据版本及有效状态、Scope内容／事件／观察epoch、来源元数据、可重建向量和关联、持久任务、事件及证据、默认关闭的情绪授权及观察。初期Persona固定mia。向量只有定长浮点Blob、模型／revision／维度及事实内容版本；此步不产生embedding。没有授权行表示关闭，迁移不会生成观察或启用追踪。30／90天策略在P20消费者执行。

现有写法仍可在回滚代码中执行；SQL触发器补扩展元数据和版本，并在修改／删除时清除旧向量／关联、失效所依赖事件。关联／事件证据禁止跨owner插入及改变关联ID。新增状态／任务／趋势的完整业务与撤销、删除、缓存处理仍分别由P12—P20实现并验收，不能以schema存在宣称已贯通。P24完整版本回滚还须验证这些消费者及派生数据；本步仅证明基础事实旧代码的必要读写兼容。

## 原子性

`schema.py` 核对旧列形状，独占自身BEGIN IMMEDIATE事务；逐条执行完整SQL（含触发器），不用隐式提交的executescript。版本1记录SQL checksum和实际扩展schema checksum，重复执行只校验；未知版本、校验值或无账本的mia_*对象拒绝覆盖。失败回滚，进程硬退出由SQLite恢复原事务。初始化失败关闭连接。

## 固定真实旧代码

服务workflow独立检出a30a5081bfa3c08e7387b9f5d9be77bd957e8175，仅取server/companion/memory.py；测试先核对SHA256 `e7b24984ad682f767d76498b9b249e6dac5362ffad8ac453c793d2c6fde47ef5`。不把重写的假旧schema当作旧版本证据。

用该真实旧MemoryStore创建活跃／敏感候选及来源，升级比对原五表完整数据与列顺序；再用同一旧代码修改、查询、新写入、跨owner保留和清空，重开新版验证一致。另验重复迁移、未知schema／checksum拒绝、关联／事件证据隔离，以及子进程在创建向量表时os._exit(77)：重开数据库必须无任何半成品mia_*对象且原数据相同，再迁移成功。测试中的零Blob明确为合成约束fixture，不是embedding结果。

所有自动测试与构建仅在GitHub Actions。P10兼容基础完成，下一步P11／P12读取本报告的精确SHA和范围；生产、实际向量、持久任务执行和八项行为均另行验收。
