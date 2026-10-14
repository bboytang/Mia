# P08／P09 App必要私有授权迁移

继续使用现有设备ID、client UUID、OTA发现、WebSocket和智控台登录。不启用旧App账户体系。

设置中只增加“私有授权”：设备所有者在已登录智控台为上述绑定设备生成一次性码，App通过HTTPS兑换，完成后回首页恢复个性化语音。授权码只在本次UI状态和HTTPS请求body中存在，完成／失败后清空；不写UserDefaults／URL／日志。移除本机凭据与智控台服务器撤销明确区分。

兑换／续期接口从既有OTA路径 `/…/ota/` 派生为同一manager根的 `/device/mia-auth/exchange`／`renew`；要求HTTPS OTA、同host的WSS，保留8002／8000等既有端口差异，拒绝查询、其他路径和跨服务器。保留平台证书／地址校验，不跟随任何重定向，不自动重试。域名不是要求，受信任IP证书同样适用。

私有凭据保存于现有Keychain服务的单独 `private-device-grant` 条目，`AfterFirstUnlockThisDeviceOnly`，包含期限和精确OTA／语音地址、设备及client约束。只有未过期且地址／设备／client匹配才附加 `Mia-Private-Credential` WSS头；旧Authorization语音令牌格式保留。凭据不发送给HTTP／WS、OTA发现或其他服务器／路径。剩余有效期小于1天时以现有凭据经HTTPS轮换；过期不凭旧弱令牌续期，需要新授权码。服务器始终复查当前授权，不信任App保存的Scope标签。

App收到 `mia_authorization/required` 立即停止会话／音频，固定显示“请用智控台授权码完成授权”，不误报解绑、不自动重新登录或循环重连。设置变更期间返回的授权结果不覆盖当前入口。

GitHub验证：协议／真实loopback WebSocket会话验证提示前不启动音频；请求与解析负例检查不安全入口、跨host／port／path／设备／client、过期及错误Persona；Simulator实际Keychain保存／读取／移除及续期body验证保留身份；现有完整UI／协议／音频回归继续。纯请求构造与fixture不证明已对实际manager通过HTTPS/WSS兑换、续期、重连及个性化恢复，实际证书／代理入口、iPhone和智控台code入口仍待贯通。

当前代码待本提交GitHub构建／测试，无本地构建或生产部署。Scope实际Java→Python集成修正绑定版本0后仍失败，增加只记录endpoint／返回类型／字段类型的脱敏定位，不把机制测试或接口存在当整链完成。
