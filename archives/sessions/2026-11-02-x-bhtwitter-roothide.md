# X、BHTwitter 与 NeoFreeBird 产物归档

日期：2026-11-02
分支：`codex/trollstore-main-isolated-20261102`

## 结果摘要

- 获取 X 12.39 的社区 NFB IPA，并生成桌面名为“X 2”、bundle ID 为 `com.atebits.Tweetie2.second` 的副本。
- 获取 NeoFreeBird 7.3.0 和原版 BHTwitter 4.4 的 rootless deb；RootHidePatcher 均生成了 arm64e deb。
- 原版 BHTwitter 4.4 随附的 TrollStore TIPA 检查显示 X 10.97.1，因此没有把它称作 X 12.39 套装。

## 产物清单

| 文件 | 实际路径 | 与任务的关系 | SHA-256 |
| --- | --- | --- | --- |
| X 12.39 NFB 原 IPA | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/X-12.39-NFB.ipa` | 社区来源的输入 IPA；ZIP 校验通过 | `c546c244de0d9dd5ded4675edf3b9e11ac45982da7b68a32dcbf166be9f215e5` |
| X 12.39 双开 IPA | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/X-12.39-NFB-Dual.ipa` | 只改主应用 Info.plist；bundle ID 为 `com.atebits.Tweetie2.second`，显示名为“X 2”；ZIP 校验通过 | `1c9363ebb691d09df57ff09689f0db9122a59d328c7539328140dd2b50eeaf99` |
| NeoFreeBird 7.3.0 rootless deb | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/com.nfb.tweak_7.3.0-1+debug_iphoneos-arm64.deb` | RootHide 转换输入，版本 `7.3.0-1+debug`，架构 `iphoneos-arm64` | `8fefba1c6bd0b0a325aa93f88205dd91a522802623d00d54ecb67600030ac635` |
| NeoFreeBird 7.3.0 RootHide deb | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/com.nfb.tweak_7.3.0-1+debug_iphoneos-arm64e.deb` | RootHidePatcher 输出，版本 `7.3.0-1+debug`，架构 `iphoneos-arm64e` | `a6c5a4a0f358b5872d9e7a7c98ff02b66d64926cde3eb15b0b750fe6accc92d3` |
| BHTwitter 4.4 rootless deb | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/com.bandarhl.bhtwitter_4.4-1+debug_iphoneos-arm64.deb` | 原版插件 RootHide 转换输入 | `4060410fd9244a5a91a9ab852f828ada7ea55552a59c645a0f30fa41668ada76` |
| BHTwitter 4.4 RootHide deb | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/com.bandarhl.bhtwitter_4.4-1+debug_iphoneos-arm64e.deb` | RootHidePatcher 输出，版本 `4.4-1+debug`，架构 `iphoneos-arm64e` | `85041a7c30fb28f0e56b0a796a6f3440cc6693385526c2be524fe6179e9c1627` |
| realpath 兼容工具 | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/dist/twitter/root-hide-compat/realpath` | 给 macOS 系统 realpath 补上脚本使用的 `--relative-base` 参数支持；未修改官方 patch.sh | `558d362d37fc1ab9102d82dbaee4f0a25e187d5dc616cc92538beb8b3210e4b8` |
| RootHidePatcher | `/Users/mac/.codex/worktrees/trollstore-main-isolated-20261102/巨魔越狱ipa插件/tools/RootHidePatcher/patch.sh` | 使用的转换脚本；上游固定提交见同目录 `UPSTREAM_COMMIT` | 仓库跟踪文件 |

## 验证与限制

- 双开 IPA 与原包包含相同 ZIP 条目；内容差异只有 `Payload/Twitter.app/Info.plist`。两个 IPA 的 ZIP 校验均通过。
- 两个 RootHide deb 的 control 信息和 data archive 均可读取；版本与架构如上。
- RootHidePatcher 对两个 tweak 都报告 dylib 中残留固定路径 `/var/jb/Library/Application Support/BHT/BHTwitter.bundle`。RootHide 使用随机 jbroot，不能保证该资源路径在设备上可用；按项目约定未手工改包。
- dpkg-deb 构建时提示归档根目录 owner/group 为 `0:501`。包仍成功生成；没有在设备上安装验证。
- 双开 IPA 的 Keychain/App Group entitlement 沿用输入包；账号数据隔离未验证。macOS 的严格代码签名检查未通过，设备安装和启动均未测试。
- 本次未修改源码或项目版本字段；大体积 IPA/deb 留在被 Git 忽略的 `dist/`，不纳入提交。

## 资料来源

- X App Store：<https://apps.apple.com/us/app/x/id333903271>
- IPA Vault 社区源：<https://raw.githubusercontent.com/927tx/IPA-Vault/refs/heads/main/ipavaultsource.json>
- BHTwitter 4.4：<https://github.com/BandarHL/BHTwitter/releases/tag/4.4>
- NeoFreeBird tweak（BHTwitter 分支）：<https://github.com/NeoFreeBird/tweak>
