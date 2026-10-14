# P08 智控台必要授权入口

在原已登录设备管理的设备操作中增加“私有授权码”与“撤销私有授权”。服务端仍核实当前操作者、真实设备绑定、Agent权限；前端显示按钮不代表获得权限，不新增账户、路由或用户数据库。

使用现有RequestService和现有登录Bearer。仅允许HTTPS页面访问同源HTTPS接口，生成码／撤销均单次请求、无自动重试。新敏感请求不打印原始错误对象，避免错误日志含认证头或返回码；其他请求保持现有行为。码仅为弹窗内存状态，关闭、销毁或10分钟后清理，不写localStorage／URL／缓存。撤销保留原设备绑定。

新增补丁 `server/admin_web/private-authorization.patch`，按原生产dialog、responsive补丁之后应用；既有源文件完整preimage检查覆盖新增httpRequest文件。只增必要按钮、弹窗、方法及敏感日志选项，不重写智控台登录、现有请求或响应式架构。

GitHub继续全部原前端单测／snapshot、构建及四浏览器多尺寸回归；新增HTTP拒绝与合成HTTPS页面下生成／关闭／撤销检查，验证复用登录、仅正确设备body、没有解绑、无自动重试和码不持久化。HTTPS页面由浏览器route供应静态资源与mock API，是UI／请求规则测试；实际证书／代理／Java签发整链和真机另行验收，不能据此声称生产HTTPS已通过。

当前：必要实现和浏览器用例待本提交GitHub验证，未部署。身份manager→Python代码 `0589665b51482f1422ebd172be360c490e07be65` 的 [38626866860](https://github.com/bboytang/Mia/actions/runs/38626866860) 17身份用例及构建通过；全量167中166通过／唯一既有脱敏失败，0error／skip，整体workflow保持failure。P09完整并发、App实际WSS、P16任务及八项行为仍未验收。
