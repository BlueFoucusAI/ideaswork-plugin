# 本地 Runtime Core（npm 安装）

本插件不内置原生程序。只有下列本地命令需要它：`runtime checkout`、`runtime python`、`runtime wait-result`、
`material upload`、`skill push`（上传本地 Skill 草稿，见 ideaswork-builder）。Remote MCP 的目录查询、API 调用、
Skill 版本管理等不依赖它，不要为这些先安装。

插件固定使用 npm 包 `@ideaswork/cli-dev@2026.1030.163810-dev`（渠道 `dev`），版本与插件一致。
不要改用其他版本，也不要使用 PATH 上来源不明的 `ideaswork`。

## Windows（原生，无需 WSL）

本文与 Skill 里的 `sh <plugin_root>/runtime/bin/ideaswork` 在 Windows 原生环境换成 `.cmd` 启动脚本：

- cmd.exe：`<plugin_root>\runtime\bin\ideaswork.cmd ...`
- PowerShell：`& "<plugin_root>\runtime\bin\ideaswork.cmd" ...`

cmd.exe 会改写引号、`%` 和 `&`，所以 Windows 上**不要把 JSON 直接写在命令行**：先把 JSON 写进工作区内的
临时文件，再用 `@文件` 传入 `--linked-json`、`--tasks-json`、`--params-json`、`--completion-json`、`--body`、
`--args-json`、`--python-path-json`；lease 仍用 `--runtime-lease-stdin` 从标准输入传，不进命令行。
`runtime python` 需要本机 Python 3.10+，依次查找 `python3`、`python`、`py -3`（会跳过 Microsoft Store 的占位程序），
也可用 `--python-executable` 指定。

## 先检查

```bash
sh <plugin_root>/runtime/bin/ideaswork --json version
```

- 成功且 `version` 为 `2026.1030.163810-dev`：直接使用 Skill 里的 runtime 命令。
- 失败（`native_binary_missing`、找不到 npx、版本不一致）：按下面安装。

`runtime python` 另需本机 Python 3.10+（macOS 自带的 python3 是 3.9）。不满足时返回 `python_version_unsupported`、脚本不执行；
请用户安装 3.10+ 后用 `--python-executable <路径>` 指定。Node.js 低于 22 时启动入口直接报 `node_version_unsupported`。

## 安装（先让用户知情）

简短告知用户：需要 Node.js 22+ 和网络；会全局安装 `@ideaswork/cli-dev@2026.1030.163810-dev`，并把校验过 SHA-256 的原生程序
下载到 `~/.ideaswork/npm/dev/`；不会登录，也不会读取或修改 IdeasWork 登录状态。
用户拒绝则不安装，并如实说明依赖本地命令的步骤无法执行。

```bash
sh <plugin_root>/runtime/bin/ideaswork install --components runtime --native install --yes
```

安装后重新执行上面的检查。

## 失败时

- 没有 Node/npx：请用户安装 Node.js 22+；不要用其他方式下载原生程序。
- 沙箱没有网络：第一次运行某个版本需要联网安装；脚本会明确提示「当前环境没有网络」，请用户放开网络权限后重试。
  已安装过该版本后不再需要网络（启动脚本直接运行 `~/.ideaswork/npx` 里的同版本程序，不再经过 npx）。
- `npm 操作失败`（常见为全局目录无权限）：如实告诉用户，由用户处理 npm 全局目录权限；不使用 sudo。
- 下载或校验失败：如实报告，不绕过校验，不手工复制二进制。
- 插件更新后版本变化：重新检查并安装；旧版本程序不受影响，也不会清理任务状态。

Runtime Core 只使用宿主下发的 lease（`--runtime-lease-stdin`），不读取 CLI OAuth，也不回退其他身份。
