# XHSNoRefresh 0.1.0 检查记录

## 已完成

- 18 项 macOS 策略测试通过：识别 iOS `v6` 和 web-style `homefeed`、只拦截已识别的自动刷新标记、
  触摸后放行、保留翻页、忽略无关接口、支持关闭开关。
- Python 构建脚本语法检查通过。
- 同一源码编译为 arm64 与 arm64e，合成通用动态库并通过 ad-hoc `codesign --verify --strict`。
- RootHide deb 成员、控制信息、应用过滤配置和 `md5sums` 已检查。
- 公开资料中存在与本需求相同的用户反馈：打开 App 先显示感兴趣的首页内容，随后无操作自动刷新，
  刚显示的内容消失。[公开反馈](https://www.sina.cn/news/detail/5342150234997216.html)

## 尚未完成

- 没有用户当前版本的小红书 IPA，也没有目标手机抓包；尚未证明当前版本确实经过
  `NSURLProtocol`/`NSURLSession` 这两层。
- 尚未在手机上验证冷启动、回前台、手动下拉、无缓存首次安装和后台网络行为。
- 如果 App 使用自有网络栈，或更新后改变 `refresh_type`，插件需要根据真机日志增加对应 Hook；
  不能仅凭本机编译结果宣称已修好。
