# RootHidePatcher（macOS 转换脚本）

这里保存 RootHide 官方仓库的 macOS `patch.sh`、权限文件和许可证。源文件取自官方仓库提交 `80c16e08da33fecd27c0ff35777f37afd171868b`；脚本只清理了行尾空白，没有改动转换逻辑。

## 本机安装

- 工作区副本：`tools/RootHidePatcher/`
- 本机稳定副本：`~/.local/share/RootHidePatcher/`
- 命令入口：`~/.local/bin/roothide-patch`（该目录已在本机 `PATH` 中）

本机已通过 Homebrew 安装 `ldid-procursus`、`dpkg`、`gnu-sed` 和 `findutils`。转换脚本还会使用 macOS 自带的 `file`、`awk`、`otool`、`install_name_tool` 等工具。`dpkg` 在此仅用于 `dpkg-deb`，没有配置为安装系统软件包。

## 使用

```sh
sudo roothide-patch /路径/原始插件.deb /路径/RootHide插件.deb
```

脚本要求以 root 身份运行。建议明确指定不同的输出路径以保留原包。官方脚本不支持所有插件；遇到不支持的架构、包名或转换错误时，应保留原包并按结果处理。macOS 下脚本会把临时解包目录放在输入文件旁，完成后不会自动清理这些目录。

## 上游

- 仓库：[RootHide/RootHidePatcher](https://github.com/RootHide/RootHidePatcher)
- 上游说明：[README](UPSTREAM_README.md)
- 固定提交：`80c16e08da33fecd27c0ff35777f37afd171868b`
