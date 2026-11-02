# VVeboFix 合并版 1.1.0 检查结果

## 实际完成

基于本地 main `17891f8` 新建独立 worktree 与 `codex/vvebo-unified` 分支。
这一版本先在独立分支实现、编译和验证，再纳入本地 main 并推送到新建的公开仓库。
将仓库内 `purchase_compat/` 的已购模块与固定版本的上游 VVeboFix 源码合编。

生成的 `VVeboFix.dylib` 包含两部分实现，且每种架构只有一个自动初始化入口。
deb、供 TrollFools 注入的 dylib、预注入 IPA 内的合并库逐字节一致。

## 编译与本机运行检查

执行 `python3 combined/build.py --ipa <用户提供的原始全权限 IPA>`，正常退出。

- 已购启动顺序检查 8 项、原有行为检查 10 项、两模块共存及网络行为检查 23 项，共 41 项通过。
- 同一组源码完整编译为 iOS arm64、arm64e，再合成通用动态库；编译启用 `-Wall -Wextra -Werror`。
- 两个架构切片分别通过严格签名检查，仅依赖系统库；每个切片只有一个 constructor。
- 统一初始化按实际顺序先安装网络逻辑、再安装已购逻辑；测试确认不会提前触发模拟 MMKV 初始化。
- 网络检查覆盖请求地址和翻页参数转换、个人主页卡片转换、置顶标记、粉丝推荐过滤、无关数据回退、
  非法 JSON 回退、请求递归标记，以及两类 NSURLSession 配置。没有发送真实微博请求。

## 最终包检查

- deb 使用 `com.lhl.vvebofix` / `1.1.0` / `iphoneos-arm64e`，原生 RootHide 路径。
  包中只有一个 dylib 和一个对应的应用过滤配置，过滤到 `com.johnil.vvebo`。
- 原 VVeboFix 同包升级；对单独已购兼容包和旧 com.yourcompany 包声明 Conflicts / Replaces。
- Debian ar 成员、root 所有权、文件权限及所有文件 md5sums 通过。
- 输入 IPA 的既有代码节、Info.plist 和原始权限保持一致，主程序只新增一次合并库加载命令。
- App 和全部嵌套框架通过 `codesign --verify --deep --strict`。
- 最终 IPA 的 ZIP 校验通过，全部 244 个文件与已验证签名的 App 一致。

## 尚未完成的手机验证

原 VVeboFix 1.0.1 收到过“注入成功”反馈，不代表重编译后的合并版通过手机测试。
单独已购兼容 0.1.0 曾白屏；0.1.1 修复了已复现的提前初始化缺陷，但还没有手机成功反馈。
因此本次不能宣称手机白屏、高级功能或真实接口访问已经修好。

目标环境 iOS 17.3.1 / Relaxin 与 iOS 17.0 / TrollStore 都尚未运行合并版。
待测试：冷启动、个人主页、粉丝列表、Pro 状态、换肤与重启后保留、iCloud 开关与实际上传下载。
只有 IPA，没有 VVebo App 源码；已完整编译插件并重打包整个 App，不能执行整个 App 的源码编译。
