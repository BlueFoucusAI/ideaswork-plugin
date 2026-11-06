# Windows 原生环境执行（PowerShell 优先）

Windows 上没有 `sh`，Runtime Core 的入口、临时授权和 JSON 参数都要换写法。本文件只讲**在哪里启动、
怎么把 lease 送进去、失败怎么判**；业务 Skill、授权边界和远端 API 准入不变。

## 三条硬规则

1. **只用原生 Windows PowerShell 启动 CLI**：`& "<plugin_root>\runtime\bin\ideaswork.cmd" ...`。
   不要在宿主的 JavaScript/Node 执行环境里用 `child_process` 启动 `ideaswork.exe`，也不要走 WSL / `sh`。
2. **lease 只走标准输入管道**：`$lease | & <入口> ... --runtime-lease-stdin`。不要用环境变量、
   子进程 `input` 通道、继承句柄、命令行参数或临时文件传 lease。
3. **JSON 参数先写文件，再用 `@文件`**：`--linked-json`、`--tasks-json`、`--params-json`、
   `--completion-json`、`--body`、`--args-json` 都支持；内联 JSON 会被 cmd.exe/PowerShell 改写引号。

已知的失败与成功路径（真实 Windows 主机）：

| 此前失败的方式 | 正确方式 |
|---|---|
| 在 JavaScript/Node 执行环境里通过 `child_process` 启动 `ideaswork.exe` | 通过原生 Windows PowerShell 启动同一个 `.cmd` / `.exe` |
| 使用子进程输入通道或环境变量传临时授权 | 使用 PowerShell 管道把 lease 喂给 `--runtime-lease-stdin` |
| 立刻返回 `command_failed`，没有保存文件 | 正常下载主 Skill 和全部 linked 依赖 |

## 入口对照

| 场景 | Unix / WSL | Windows 原生 |
|---|---|---|
| 插件 Runtime Core | `sh <plugin_root>/runtime/bin/ideaswork ...` | `& "<plugin_root>\runtime\bin\ideaswork.cmd" ...` |
| 独立 CLI | `ideaswork ...` | `& ideaswork ...`（PowerShell 解析 npm 生成的 `.cmd` 包装器，或按 README 用原生 `ideaswork.exe` 绝对路径） |
| Python 脚本 | `ideaswork runtime python ...` | `& ideaswork runtime python ...` |
| 等待异步 | `ideaswork runtime wait-result ...` | `& ideaswork runtime wait-result ...` |

插件只带薄 `.cmd` 启动脚本，不含原生程序；首次使用按需安装同版本 Runtime Core，不需要 WSL。
独立 CLI 与插件各用自己的身份/运行时，不能互相顶替。

## lease：管道，不是参数

```powershell
# $lease 由宿主注入当前会话，只有一行；命令文本里只出现 --runtime-lease-stdin
$lease | & "<plugin_root>\runtime\bin\ideaswork.cmd" runtime checkout `
  --workspace "<workspace>" --skill-name "<skill_name>" --checkout-id "<checkout_id>" `
  --linked-json "@<workspace>\.avp_run\linked.json" `
  --runtime-endpoint "<endpoint>" --runtime-lease-stdin --json
```

- `--runtime-lease-stdin` 读取标准输入的**第一行**（上限 64 KiB），空输入报 `Missing lease on stdin`。
  管道里只放 lease 本身，不要混提示文字或第二个值。
- 不要用命令行参数传 lease（CLI 不接受 `--runtime-lease`），也不要用 `$env:` 变量、子进程 `input`
  选项、继承句柄或工作区文件；同一 lease 的 Runtime Core 调用串行执行，不并发。
- 已知宿主的 JS/Node `child_process`（`input` 选项、继承句柄）和环境变量两条通道在 Windows 上
  都不稳定，可能直接 `command_failed` 或让原生入口读不到 lease；PowerShell 的 `|` 提供真实 stdin
  管道，是实际可用的方式。
- 命令执行后不要回显 lease；失败日志里不复制它的值。

## JSON 参数与路径

```powershell
'[]' | Set-Content -Encoding ascii .\linked.json
& "<plugin_root>\runtime\bin\ideaswork.cmd" runtime checkout `
  --workspace "$PWD" --skill-name "main" --checkout-id "<id>" `
  --linked-json "@.\linked.json" --runtime-endpoint "<endpoint>" --runtime-lease-stdin --json
```

- JSON 文件参数必须带 `@` 前缀（`--linked-json "@.\linked.json"`），支持相对当前目录的路径；
  文件放任务私有目录，不要放共享盘或提交到仓库。
- 路径含空格、中文或 `&` 时整体加引号；`--workspace` 用 PowerShell 解析后的绝对路径，避免
  `~`、`%VAR%`（cmd）/ `$env:`（PowerShell）在不同 shell 下展开不一致。
- checkout 的输出仍是路径唯一权威：用返回的 `workspace_dir` / `runtime_dir`，不要自己拼。

## 失败怎么判

`command_failed`（`Local runtime command failed`、退出 1、stderr 为空）只说明**本地这条命令没跑起来**，
不是网络、权限或 Skill 缺失的证据。已知两类成因，按顺序排查：

1. **调用方式**：是否在 JS/Node 执行环境里、用了 `sh`/WSL，或把 lease 走了 env/input 通道。改成
   PowerShell + 管道 + `--runtime-lease-stdin`，用**同一份** lease 和 checkout 参数原样重跑一次。
2. **本地落盘**：若返回 `local_io_error`，按 message 里的操作、路径和系统原因处理——工作区被杀毒软件、
   云同步盘、编辑器占用，或 Controlled Folder Access 拦截；换到本地普通目录再试。
3. 仍是 `command_failed` 且目标目录为空：停止重试（同一问题最多三次），报告启动方式、工作区路径和
   原始错误。**不要重新 `pull_skill`、不要换工作区、不要改 Skill**，也不要把这个错误说成网络或权限问题。

重跑同一个 checkout 只是重做归档下载与落盘，不创建业务任务、不产生生成费用；仍沿用原 lease 和原
checkout 参数，不要为了“清理状态”删目录、重新 pull 或重建 Context。

## Python 与等待

- `runtime python` 需要本机 Python 3.10+；Windows 依次探测 `python3`、`python`、`py -3`，会跳过
  Microsoft Store 的占位程序。返回 `python_version_unsupported` 时请用户安装 3.10+ 并用
  `--python-executable` 指定，不改脚本、不裸跑 `python script.py`。
- `runtime wait-result` 与 checkout 用同一条 stdin lease 通道；`--tasks-json` 走 `@tasks.json`。
  仍有 `--state-file` 续等，不要用 PowerShell `Start-Sleep` 或循环 `--max-polls 1` 充当轮询器。
- 超时退出 `3`、中断退出 `130` 的语义与 Unix 相同；续等用 `--resume`，不重新创建任务。

## 不要做

- 不要在宿主 JS/Node 沙箱里 spawn CLI，再把 `command_failed` 当成 lease 失效或 Skill 有问题。
- 不要用 `cmd /c` 拼一长串内联 JSON；不要为了绕过引号问题改成写死参数。
- 不要用 WSL、裸 HTTP、旧 `avp_local` 或另一个 CLI 身份替代原生 PowerShell 入口。
