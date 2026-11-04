# 小红书防自动刷新 / XHS No Startup Refresh

这是一个面向小红书 iOS 客户端的越狱插件，目标是解决“打开 App 先显示一批内容，
随后没有任何操作就自动刷新，刚才的笔记消失”的问题。

## 工作方式

- 在小红书启动、或从后台回到前台时开启保护状态，默认一直持续到用户互动。
- 只拦首页 `homefeed` 的初始请求；当前公开抓包里的 iOS 接口是
  `/api/sns/v6/homefeed`，自动请求常带 `refresh_type=2`。
- 用户发生触摸或滚动后立即放行，手动刷新和翻页请求不拦截。
- 同时覆盖 `NSURLProtocol` 和 `NSURLSession` 两层；如果新版 App 使用完全自有的
  网络栈而不经过这两层，插件不会生效，需要根据该版本的真机日志继续适配。

## 支持的宿主

- `com.xingin.xhs`
- 旧版 `com.xingin.discover`

## 安装与关闭

本项目提供三种越狱 `.deb` 和一个 TrollStore/TrollFools 动态库。文件名统一使用
“中文名-版本-环境”格式：

| 环境 | 文件名 | 安装位置 |
| --- | --- | --- |
| Rootful | `小红书防自动刷新-0.1.0-rootful.deb` | `/Library/MobileSubstrate/DynamicLibraries` |
| Rootless | `小红书防自动刷新-0.1.0-rootless.deb` | `/var/jb/Library/MobileSubstrate/DynamicLibraries` |
| RootHide | `小红书防自动刷新-0.1.0-roothide.deb` | RootHide 的动态库目录 |
| TrollStore / TrollFools | `小红书防自动刷新-0.1.0-1-trollstore.dylib` | 注入到小红书进程 |

安装与你的环境相符的 `.deb` 后，完整退出小红书再重新打开。TrollStore 版本是动态库，
需要用 TrollFools 或其他支持动态库注入的 TrollStore 工具加载；本项目没有用户当前版本
的小红书 IPA，因此不伪造预注入 IPA。

插件没有新增设置页面；可通过应用偏好关闭：

```sh
defaults write com.xingin.xhs XHSNoRefreshDisabled -bool YES
defaults write com.xingin.xhs XHSNoRefreshWindow -float 12
```

改完后完全退出并重新打开小红书。删除 `XHSNoRefreshDisabled` 或写成 `NO` 即恢复启用。

## 限制

公开讨论中已经有人描述过同样的现象：App 打开后先显示一批感兴趣的内容，什么都没点就
自动刷新，刚才的图文随即消失。见[公开反馈](https://www.sina.cn/news/detail/5342150234997216.html)。

本机可以编译、运行策略测试并验证动态库签名；用户已经反馈一次真实设备安装成功，
但没有提供对应 IPA、设备、系统和 App 版本，所以不能把这次结果外推为所有版本兼容。
如果其他版本安装后出现首页空白或无内容，先删除插件；这通常表示使用了未覆盖的网络路径，
或请求标记已经变化，此时应根据真机日志适配，而不是扩大拦截范围误伤首次加载。
