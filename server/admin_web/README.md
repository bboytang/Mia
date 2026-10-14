# 小智管理后台统一响应式改造

本目录是现有管理后台的源码补丁和验证工具，不是第二套后台。目标源码为
`xiaozhi-esp32-server` v0.9.7 / `87c6df77b0220ddbd8fc804f984f83f69f3225e5`，沿用 Vue 2、Element UI、Vue CLI，API、路由、认证、数据库不变。

## 构建与源码

不要修改生产压缩 JS。将上游源码检出到独立目录后执行：

```sh
python3 server/admin_web/apply.py /path/to/xiaozhi-source
python3 server/admin_web/apply.py /path/to/xiaozhi-source --apply
```

默认仅检查，不写文件；逐个校验修改文件的原始 SHA256，发现已有定制或重复安装立即拒绝覆盖。审阅自定义差异后再人工合并，不通过重置生产代码来满足校验。

`.github/workflows/mia-admin-responsive.yml` 在 GitHub Actions 完成：原版构建与生产静态文件对比、原有单元/契约/快照回归、新版生产构建、Chromium/Android Chrome 模拟、WebKit/iOS 模拟、Firefox 的全路由尺寸和交互测试。产物包含可维护的完整前端源码、静态文件、校验值、截图、报告和提交标记。测试使用合成账号与数据，不访问生产或调用模型服务。

## 修改范围

`responsive.patch` 的修改文件可用 `git apply --stat server/admin_web/responsive.patch` 查看：

- `public/index.html`：安全区域 viewport。
- `src/App.vue`：移除独立 H5 跳转，所有设备使用原应用。
- `src/main.js`、`src/utils/responsive.js`、`src/styles/responsive.scss`：统一宽度断点、视觉视口、页面布局、表单、弹窗、抽屉和触控规则。
- `HeaderBar.vue`：复用原导航项及权限判断，紧凑屏幕折叠菜单。
- `CustomTable.vue`、`CustomPagination.vue`：手机卡片复用字段插槽、操作与选择；分页按钮调整。
- `DeviceItem.vue`：触控操作和完整提示词查看。
- `ProviderDialog.vue`、`TtsModel.vue`、`ModelConfig.vue`：宽表格列最小宽度与触屏详情。
- 全部带路由的页面：限定响应式样式作用域；知识库文档子页面通过父页面继承规则。
- 六种现有语言字典：导航、关闭与记录选择文案。

桌面断点大于1180px，紧凑导航不改变菜单内容。600px及以下，共用表格显示卡片；模型、参数和音色管理的复杂表格保留局部滚动。平板主要保持桌面表格，导航和内容随宽度调整。虚拟键盘使用 visualViewport 限制弹窗高度，保留浏览器自然滚动和缩放能力。

## 部署前检查和回滚

当前生产Web镜像同时包含 Nginx 静态前端和 Java manager-api。前端发布必须保留运行镜像中的现有 JAR、启动脚本、Nginx API代理、Compose覆盖、端口、环境与数据卷；不要重新构建上游Java以覆盖Mia认证扩展。

1. 核对CI对应提交全部通过，查看 `baseline/comparison.txt`。原版构建未全部匹配生产时，先核对构建依赖和实际定制，不直接替换现有前端。
2. 再次记录运行Web镜像 ID、`/app/xiaozhi-esp32-api.jar` SHA256，以及生产静态文件清单；生产变化后重新核对。给当前镜像加唯一回滚标签，备份三份Compose和Nginx配置到非公开受保护目录。
3. 从已验证的CI产物准备新版本。派生镜像以**当前生产Web镜像ID**为基础，只复制前端静态资源。保留旧的 `js/`、`css/`、`img/`、`fonts/` 带hash资源供已有桌面会话延迟加载；用新版 `index.html` 和 Service Worker 清单提供新入口。不要在发布时清空旧资源。
4. 在隔离环境启动候选镜像，用合成数据检查路由、登录、功能与布局；校验新旧JAR一致、API路径与监听端口一致。不要让隔离测试进程连接生产数据库或使用生产密钥。
5. 发布前安排短暂维护窗口：现有Web容器含Java，替换Web镜像会短暂重启管理API。仅修改 `docker-compose.mia.yml` 中 `xiaozhi-esp32-server-web.image`，保留其他配置。使用现有三份Compose，仅重建Web：

   ```sh
   cd /opt/xiaozhi-server
   docker compose -f docker-compose_all.yml -f docker-compose.lowmem.yml -f docker-compose.mia.yml up -d --no-deps xiaozhi-esp32-server-web
   ```

6. 检查 `http://43.143.230.174:8002/` 与 `/xiaozhi/` 代理、已登录会话、普通用户与管理员权限、设备操作及配置保存。确认语音/MySQL/Redis容器没有被重建。HTTPS用户还需检查Service Worker更新；首次打开新版本可能需要刷新。
7. 失败时恢复本次备份的Compose镜像配置，使用同一命令仅重建Web。确认原镜像和JAR恢复；不回滚数据库，不删除记忆或设备绑定。

本补丁不自动部署、替换文件、重启服务或操作数据。回滚基于**本次发布前**镜像，不能回滚到Mia扩展前的旧Web镜像。

## 真机验收

自动化WebKit和Android模拟不能替代iOS Safari/Android Chrome真机。须分别检查安全区域、打开/关闭真实键盘、焦点输入、下拉选择、横竖屏、长列表、上传下载、音频播放、所有配置保存/取消与权限。真实后台端到端登录和写操作需要测试账号/测试设备，避免修改当前业务数据。
