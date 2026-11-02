# VVeboFix 合并版 1.1.0

在同一份 `VVeboFix.dylib` 中合并微博主页/粉丝接口修复和本机已购兼容。
适用于 VVebo 3.3.31；预注入 IPA 对应用户提供的全权限砸壳构建 4。
动态库同时包含 arm64、arm64e，只直接依赖系统库，无需其他配套 dylib。

## 安装方式

- **Relaxin / RootHide 越狱：** 安装 `com.lhl.vvebofix_1.1.0_iphoneos-arm64e.deb`。
  它升级同包标识的 VVeboFix 1.0.1；与单独的已购兼容包、旧 com.yourcompany 包冲突，
  请允许包管理器移除旧包。完全关闭 VVebo 后再打开。
- **巨魔 / TrollStore：** 将 `VVeboFix_Combined_1.1.0_TrollStore.dylib` 用 TrollFools
  注入原始 VVebo；注入前移除原 VVeboFix 和 VVeboPurchaseCompat 的手动注入记录。
  或者用 TrollStore 安装 `VVebo_3.3.31_Combined_1.1.0_TrollStore.ipa`，其中已包含合并库。

以上只选一种加载方式。预注入 IPA 不再额外注入 dylib，也不同时开启 deb。
越狱设备不需要为了合并换 App，优先使用 deb。

原已购兼容 0.1.0 曾白屏，0.1.1 修复了本机可复现的提前初始化问题，
但未收到 0.1.1 手机成功反馈。合并版保留此修复，仍是待手机验证的版本。
本机授权读取不改写原存储，不生成 Apple 交易或收据；真实 iCloud 同步仍依赖原 App、
账号、权限与服务，不能用开关可开启代替上传下载测试。

## 构建

```sh
python3 combined/build.py --ipa '/完整路径/原始VVebo.ipa'
```

构建会运行已购行为、启动顺序及合并后的网络逻辑检查，再完整编译两种架构的插件。
传入原 IPA 时重打包整个 App，保留既有代码节和原有权限，验证全部签名。
没有 App 源码，不能进行整个 VVebo 的源码编译。输出只在忽略的 `dist/combined/` 中，
不提交到 Git。

## 手机复测与恢复

先确认冷启动可进首页，再检查个人主页、粉丝列表、Pro 状态、换肤与重启后保留。
iOS 17.3.1 / Relaxin 和 iOS 17.0 / TrollStore 都尚未实际运行合并版。
若越狱版异常，卸载合并版后可重新安装此前成功注入的 VVeboFix 1.0.1。
巨魔版可在 TrollFools 移除合并库，或覆盖回原始 IPA；先保留原 IPA 与个人数据备份。
