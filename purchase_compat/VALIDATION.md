# VVebo 已购兼容 0.1.1 检查结果

目标：VVebo 3.3.31（构建 4），iPhone 15 Pro Max / iOS 17.3.1 / Relaxin 0.5.6。

## 0.1.0 手机失败与 0.1.1 修复

用户实际安装 `com.local.vvebo.purchasecompat_0.1.0_iphoneos-arm64e.deb` 后停在白色加载页；
卸载该插件并重开后恢复正常。此前 VVeboFix 1.0.1 继续保留。

本机对旧源码补充启动顺序测试，实际得到：

```text
PASS: Class lookup leaves storage initialization dormant
PASS: Compatibility installs before app startup
FAIL: Installing does not force storage +initialize before app startup
```

额外调用栈和反汇编确认，ARC 会在 `@synchronized (storeClass)` 入口保留类对象；
该动作通过 `objc_retain` 提前调用存储类的 `+initialize`。
App 自带 MMKV 在 `0x70a4` 的 `+initialize` 中，于 `0x71b8` 调用
`UIApplication.sharedApplication`，随后读取 `applicationState`。
原插件在进程加载阶段执行安装，因此存在在 App 正常启动前提前运行该代码的问题。
`mmapID` 在 App 自带 MMKV 中只是直接读取实例字段，未发现该读取器加锁的证据。

0.1.1 仅把安装器对类对象的 `@synchronized` 换为 C 互斥锁，日期结果和范围保持原样。
新增测试在此修改后通过，覆盖首次安装、重复安装均不提前初始化，正常使用时再初始化，
以及随后兼容读取与原方法回退仍正常。这验证了本机可复现的启动顺序缺陷已修复；
尚无手机调用栈，不能据此断言这就是手机白屏的全部原因。

## 定位依据

- 原 App 的公共授权日期读取器通过 MMKV getDateForKey: 读取 expireDate。
- 设置存储标识为 com.johnil.vvebo；购买状态及 iCloud 授权分支都调用该读取器。
- 原 App 的永久授权判定阈值为 Unix 秒 31536000000。
- 兼容层将对应字段的本机读取结果视为长期有效，原存储值不写入。

## 已执行并通过

- 同一 Objective-C 源码的 macOS 原生检查：启动顺序 8 项、原有行为 10 项，共 18 项。
- iOS arm64 动态库完整编译，最低 iOS 14.0，只直接依赖系统库。
- RootHide deb 的成员、元数据、安装路径、所有权、权限、校验和与应用过滤配置。
- 从最终 deb 解出的动态库签名；deb 与 IPA 中的插件逐字节一致。
- 全 App 与全部嵌套框架的 codesign --verify --deep --strict。
- 最终 IPA 每个文件与已验证 App 的内容一致，ZIP 校验通过。
- App 的全部原 __TEXT 节、应用信息、iCloud 和 App Group 等原始权限保持不变。
- 仅新增明确的兼容库加载命令，没有改写原 App 功能代码。

## 尚未验证

没有在手机上运行 0.1.1。先复测冷启动，再检查 Pro 页状态、换肤和重启后保留；
iCloud 开关以及真实上传/下载也均待用户测试。0.1.0 的手机白屏反馈已记为失败。
拥有 IPA 而没有 App 源码，不能进行整 App 的源码编译；本轮执行了插件编译与整个 IPA 的重新打包和签名检查。
先前 VVeboFix 1.0.1 的“注入成功”反馈不代表本次已购兼容插件通过手机测试。

## 原始文件

原 IPA 保持不变。完整 App 和分析输出只在忽略的 `build/`、`dist/` 中。
原 IPA 保持不变。完整 App 和分析输出只在忽略的 build/、dist/ 中，不加入 Git。
