# VVebo 已购买功能兼容

兼容插件版本：`0.1.1`（待手机复测）。目标 App：VVebo `3.3.31`（构建 `4`）。
目标手机：iPhone 15 Pro Max、iOS 17.3.1、Relaxin 0.5.6。

本任务基于用户已购买软件的说明，处理侧载后本机 Pro 状态无法恢复的情况。
用户报告的现象是换肤受限、VVebo Pro 提示试用且报 `Invalid product ID`、iCloud 同步受限。

## 启动修复与测试状态

用户安装 `0.1.0` deb 后出现白色加载页，卸载后恢复正常；该版不再用于测试。
本机已复现：旧安装器的 `@synchronized (storeClass)` 会因 ARC 保留类对象而提前触发
MMKV 的 `+initialize`。App 自带 MMKV 的该方法会访问 `UIApplication.sharedApplication`，
不适合在进程加载阶段提前运行。`0.1.1` 只将此处改用 C 互斥锁，保持原来的日期处理逻辑。
这解释了一个确实存在的启动顺序问题，是否完全解决手机白屏仍需真机复测。

## 已定位的逻辑

全权限砸壳包的主程序 UUID 为 `595ED4FF-9558-308B-93C6-33EB09125340`。
它通过 MMKV 的 `getDateForKey:`，从 `com.johnil.vvebo` 存储读取 `expireDate`。
该公共读取函数被购买状态、界面和 iCloud 功能检查调用。
Pro 状态更新代码将超过 `31536000000` Unix 秒的日期视为永久授权。

插件只在 VVebo 3.3.31 中，为上述存储、上述字段返回 `NSDate.distantFuture`。
这会将本机功能授权按长期有效处理。原有存储值不写入、不修改，其他日期走原方法。
插件不生成苹果交易或收据；iCloud 登录、容器、网络及实际同步仍使用 App 原逻辑。

## 构建和交付

```sh
python3 purchase_compat/build.py
```

构建会完整编译 iOS 插件，运行同一源码的 macOS 启动顺序与行为检查，生成 RootHide deb。
传入 `--ipa` 和全权限砸壳 IPA 路径时，还会加入进程内插件并重新签名整个 App。
只有 IPA、没有 App 源码，因此整 App 的源码编译不可执行；进行的是插件编译和 IPA 重打包。
原始 IPA 不修改，主程序既有功能代码不改写，应用标识和原始权限保留。

完整 App 和分析输出仅保存在忽略的 `build/`、`dist/`，不加入 Git。

## 手机测试

两种方式任选一种：

- 安装 RootHide deb：适合保留当前 App，使用 Sileo / Irisin 安装，并允许 VVebo 加载插件。
- 安装处理后的 IPA：用 TrollStore Lite 覆盖当前 VVebo，保持应用标识不变，不先卸载。

本插件与已定稿的 VVeboFix 1.0.1 分工不同：原 VVeboFix 继续修复微博接口，继续保留即可。
兼容插件只选择 deb 或预注入 IPA 一种方式加载。
从 `0.1.0` deb 升级时，用 `0.1.1` deb 替换后完全关闭并重新打开 App。
若使用了 TrollFools 手动注入的同名动态库，也需要移除那一份，避免重复加载旧代码。

测试重点：冷启动、Pro 页状态、换肤保存与重启后保留、iCloud 开关及实际上传/下载。
本机检查不能替代这些手机测试；尤其不能将“允许开启同步”当作“实际同步成功”。
卸载 deb 或覆盖回原 IPA 可移除对应加载方式；原有本地授权日期未被写入。
