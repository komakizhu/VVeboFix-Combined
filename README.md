# VVeboFix

将 VVebo 主页/粉丝列表接口修复与本机已购功能兼容合并到一份通用动态库，提供
Relaxin / RootHide deb、TrollFools 注入用 dylib，以及预注入 TrollStore IPA。

当前合并版为 **1.1.0**，目标 App 为 VVebo 3.3.31。注入库同时包含 arm64 与 arm64e。
越狱版目标为 iOS 15 及以上的 RootHide 环境；巨魔版应先确认设备与 App 能加载相应切片。

## 安装

- **Relaxin / RootHide：** 安装 `dist/combined/com.lhl.vvebofix_1.1.0_iphoneos-arm64e.deb`。
  同包升级 VVeboFix 1.0.1，并替换独立已购兼容包。包管理器可能提示移除旧兼容包。
- **TrollFools：** 将 `dist/combined/VVeboFix_Combined_1.1.0_TrollStore.dylib`
  注入未预注入的 VVebo。先移除旧 VVeboFix 与 VVeboPurchaseCompat 注入记录。
- **TrollStore：** 直接安装
  `dist/combined/VVebo_3.3.31_Combined_1.1.0_TrollStore.ipa`。

安装方式只选一种。不同方式不要同时加载同名库。完整关闭 VVebo 后再重新打开。
安装包由下面的构建命令生成；这些本地文件不随 Git 源码提交。

## 构建

需要 macOS、Xcode 命令行工具及 Python 3。首次构建会从固定版本的 GitHub 地址获取
VVeboFix 源码，并把临时副本放在忽略的 `build/` 目录；无需第三方 Python 依赖。

```sh
python3 combined/build.py --ipa '/完整路径/VVebo_3.3.31_全权限砸壳.ipa'
```

不传 `--ipa` 时生成 deb 和 TrollFools 用 dylib；传入原 IPA 时，也会重签并生成预注入 IPA。
只有 App IPA，没有 VVebo 的 App 源码，所以构建的是完整插件和重新打包后的 App，
不是整个 VVebo 的源码编译。

## 小红书启动防刷新插件

`xhs_no_refresh/` 是独立的 RootHide 插件原型，目标宿主为小红书
`com.xingin.xhs`（同时兼容旧版 `com.xingin.discover`）。它在启动或回到前台时，
默认一直拦截已识别的首页自动刷新请求，直到用户触摸；手动刷新和翻页仍然放行。

```sh
python3 xhs_no_refresh/build.py
```

该插件尚未在真实小红书 IPA 和手机上验证；完整说明见
[`xhs_no_refresh/README.md`](xhs_no_refresh/README.md)。

## 验证状态

本机的 41 项检查、arm64/arm64e 插件编译、RootHide 包校验及整包签名检查已通过。
合并版尚未在手机实际运行；冷启动、网络请求、Pro 状态、换肤及 iCloud 上传下载仍待实机验证。
之前独立已购兼容 0.1.0 在手机出现白屏，0.1.1 修复了可复现的启动顺序问题，
但尚无该版手机成功反馈。详见 [合并版检查记录](combined/VALIDATION.md)。

上游来源及授权信息见 [UPSTREAM.md](combined/UPSTREAM.md)。上游未附独立 LICENSE；
本仓库不为上游模块虚构授权。项目没有为整个仓库声明统一许可证。
