# VVeboFix 更新记录

## 1.1.0 — 合并版

- 将 VVeboFix 主页与粉丝列表网络修复、已购功能兼容合入单一动态库。
- 提供 Relaxin / RootHide deb、TrollFools dylib 和预注入 TrollStore IPA。
- 增加 arm64 与 arm64e 通用构建及合并后行为检查。
- 完整包检查通过；手机运行与实际 iCloud 同步尚未验证。

## 1.0.1 — 2026-11-02

- 将用户提供的 VVeboFix 动态库打包为 Relaxin / RootHide 插件。
- 调整 RootHide 搜索路径，替换巨魔特殊签名，保留原始功能代码。
- 加载规则只匹配 `com.johnil.vvebo`。
- 包结构、签名和代码一致性检查通过。
- 该 RootHide 包收到注入成功反馈；其完整网络功能未分别确认。
- 保存已测试的原始 deb，不因定稿重新升版或替换包内容。
