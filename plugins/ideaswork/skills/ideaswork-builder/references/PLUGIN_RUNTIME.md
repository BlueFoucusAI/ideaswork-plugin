# 本地 Runtime Core（npm 安装）

本插件不内置原生程序。只有下列本地命令需要它：`runtime checkout`、`runtime python`、`runtime wait-result`、
`material upload`。Remote MCP 的目录查询、API 调用等不依赖它，不要为这些先安装。

插件固定使用 npm 包 `@ideaswork/cli-preprod@2026.1015.193437-preprod`（渠道 `preprod`），版本与插件一致。
不要改用其他版本，也不要使用 PATH 上来源不明的 `ideaswork`。

## 先检查

```bash
sh <plugin_root>/runtime/bin/ideaswork --json version
```

- 成功且 `version` 为 `2026.1015.193437-preprod`：直接使用 Skill 里的 runtime 命令。
- 失败（`native_binary_missing`、找不到 npx、版本不一致）：按下面安装。

## 安装（先让用户知情）

简短告知用户：需要 Node.js 22+ 和网络；会全局安装 `@ideaswork/cli-preprod@2026.1015.193437-preprod`，并把校验过 SHA-256 的原生程序
下载到 `~/.ideaswork/npm/preprod/`；不会登录，也不会读取或修改 IdeasWork 登录状态。
用户拒绝则不安装，并如实说明依赖本地命令的步骤无法执行。

```bash
sh <plugin_root>/runtime/bin/ideaswork install --components runtime --native install --yes
```

安装后重新执行上面的检查。

## 失败时

- 没有 Node/npx：请用户安装 Node.js 22+；不要用其他方式下载原生程序。
- `npm 操作失败`（常见为全局目录无权限）：如实告诉用户，由用户处理 npm 全局目录权限；不使用 sudo。
- 下载或校验失败：如实报告，不绕过校验，不手工复制二进制。
- 插件更新后版本变化：重新检查并安装；旧版本程序不受影响，也不会清理任务状态。

Runtime Core 只使用宿主下发的 lease（`--runtime-lease-stdin`），不读取 CLI OAuth，也不回退其他身份。
