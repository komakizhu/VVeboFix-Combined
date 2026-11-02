# VVeboFix 的 Relaxin / RootHide 插件包

将用户提供的 `VVeboFix.dylib` 转为原生 RootHide 布局的 Debian 插件包。
目标为 iPhone 15 Pro Max、iOS 17.3.1、Relaxin 0.5.6；不包含 VVebo App 本体。

当前版本 `1.0.1`。用户于 2026-11-02 反馈“注入成功”并要求本地定稿。
此反馈仅确认注入成功，未分别确认启动、个人主页和粉丝列表的完整功能。

已测试的原始安装包按原样保存在
`releases/1.0.1/com.lhl.vvebofix_1.0.1_iphoneos-arm64e.deb`。
定稿不替换其功能代码或包内文档，也不因本地提交、合并而再次升版。

## 转换内容

- 安装到越狱根目录内的 `/Library/MobileSubstrate/DynamicLibraries/`，不硬编码 `/var/jb` 安装前缀。
- 加载规则只匹配 `com.johnil.vvebo`。
- 将 `/var/jb/...` 搜索路径改为 `@loader_path/.jbroot/...`，已有相同目标时去重。
- 移除输入库的 TrollStore 特殊签名，改用 SHA-256 ad-hoc 签名；库不添加额外权限。
- 包架构为 `iphoneos-arm64e`，保留输入库原有的 arm64e 机器代码。
- 使用上游包标识 `com.lhl.vvebofix`，本次兼容转换版本为 `1.0.1`。

不加入 Rootless Compat / AutoPatches：输入库只直接依赖系统库，未发现需要兼容层的第三方固定路径。
不添加 `.jbroot` 的固定目标链接，由 RootHide 的安装、加载机制管理。

## 构建

需要 macOS 的 Python 3 和 Xcode 命令行工具，不安装额外依赖：

```sh
python3 build_package.py
```

输出位于 `dist/com.lhl.vvebofix_1.0.1_iphoneos-arm64e.deb`。
`input/VVeboFix.original.dylib` 是用户提供文件的副本，原文件不改动。

构建会检查签名和实际代码节是否保持一致，生成标准的
`debian-binary`、`control.tar.gz`、`data.tar.gz`，文件在包内归 root 所有。

手机安装与测试步骤见 `INSTALL.zh-CN.txt`。
该文件保留初次打包时的测试说明，最新验证情况见 `VALIDATION.md`。
结构及签名检查通过不能代替手机启动和网络功能测试。

## 参考资料

- RootHide 路径规范：https://github.com/roothide/Developer/blob/main/roothide.md
- RootHide Patcher 的路径改写及重签逻辑：https://github.com/roothide/RootHidePatcher/blob/master/patch.sh
- 相关 VVeboFix 上游打包配置：https://github.com/nildeveloper/VVeboFix

输入二进制由用户提供，不声称与上游发布文件逐字节一致。
初始 `main` 没有提交，因此使用未提交的独立分支
`codex/vvebofix-relaxin-roothide` 和 worktree 开发。
用户确认后，通过本地提交和合并将该版本收录到 `main`；不推送、不发布或安装。
