# CLI 执行绑定

用于 CLI 型制品、只有 Shell/文件读写的 Harness，或用户明确选择独立 CLI 的任务。
本节替代入口文档中的 Remote MCP 工具、App 和 lease 调用说明；业务 Skill、授权边界和原任务目标不变。
CLI 内部仍连接同一 Remote MCP 服务，不使用旧 Local MCP、`local_rpc` 或裸 HTTP 绕过权限。

## 工作流与 API 范围

按用户意图衔接 Capability 或 Builder 时复用当前 `--task`、身份与执行成果，不要求换包。
默认优先使用 checkout 的 `api.json`。有效 grant 内的垂类/策略 API 可执行；声明外普通 API
先发现、查文档再补调，不必退出 Runner。声明外受限 API 不能靠本地改 api.json 获权。
所有调用以服务端实际准入为准；旧部署拒绝时报告限制，不换 mode/身份/入口绕过。
仅明确要求构建/沉淀 Skill 时进入 Builder，在独立草稿中编辑，不覆盖 immutable checkout。

## 身份与任务

- 使用 PATH 上的 `ideaswork`，或制品中的 `runtime/bin/ideaswork`。
  缺依赖时按制品安装说明处理。先 `ideaswork doctor --json`；仅未登录/授权失效时请用户完成
  `ideaswork login`。登录是 OAuth 设备验证码授权，浏览器可在另一台电脑/手机完成，不需要 localhost 回调；
  `--no-open` 只不自动打开浏览器，不是无人值守登录。
- 为本地任务选一个稳定、非敏感的标识，每次命令都带 `--task <task>`，或由 Harness 设置
  `IDEASWORK_TASK_ID`。不得使用平台 `avp_session_id` 作为本地 task，也不得伪造平台 session。
  不显式指定时按当前工作目录隔离；同目录并行任务必须显式使用不同 task。进入 Skill workspace
  后也复用原 task，否则会变成另一条 Context。
- CLI 登录凭证共享，任务 transport/Context 和默认 checkout 目录独立。重新登录会令旧任务身份绑定失效。
  正式制品环境由渠道固定，不支持 `--env`；未绑定源码的 `--env` 仅供开发调试。
- `--json` 成功时保留业务 payload；失败读取 `error_code / next_action / retryable`，不要靠猜错误文本恢复。

## 发现与拉取

1. 用户找线上 Skill：`ideaswork skill list --query "<用户目标>" --json --task <task>`。
   根据返回的分页信息按需翻页。不要把插件内的 Runner/Builder 或本地目录当作线上 Catalog。
   同名候选必须由用户确认，使用服务返回的 `skill_id` 精确拉取。
2. 用户选择后执行 `ideaswork skill pull "<名称>" --skill-id <id> --json --task <task>`。
   CLI 复用当前工作区或绑定 OAuth 默认工作区，建立 `skill_runner` Context，并物化主包、全部 linked、
   受管 CLAUDE.md 和 API 清单；直接拉取并继续，不先要求选择工作区。
   默认目录 `.avp_run/task-<hash>/<name>/`；实际路径以返回值为准，不硬编码。
3. **默认不切换工作区。** 仅在用户明确更换工作区，或服务端明确要求选择工作区（默认项目缺失/不可访问）时，先
   `ideaswork context list --json --task <task>`，把本次团队/项目候选和“从 A → 到 B”展示给用户。
   用户确认后 `ideaswork context use <本次context_ref> --mode skill_runner --confirm-switch --task <task> --json`；
   不带 `--confirm-switch` 会被拒绝（`workspace_switch_requires_confirmation`），**不得为让命令通过自行添加**。
   找不到 Skill、权限不足都不是切换的理由，如实告诉用户即可。
   同工作区仅切 mode 可省略 ref，并加 `--reuse-session`；不为普通后续步骤反复新开平台会话。
4. 按返回的 `workspace_dir / runtime_dir` 读取受管 CLAUDE.md 和主 SKILL.md，子技能在对应阶段才读。
   Agent 负责解释并编排 Skill；没有 `ideaswork skill run`，不要猜测这个命令。

## 平台原语映射

| 平台原语 | CLI / Host 入口 |
|---|---|
| `blue_list_apis` | `ideaswork api list --json`（只列当前已授权 API） |
| `blue_query_api_docs(code)` | `ideaswork api docs <code> --json` |
| `blue_exec_api(code, body)` | `ideaswork api exec <code> --body @body.json --json` |
| `blue_exec_batch(calls)` | `ideaswork api batch --calls-json @calls.json --json` |
| `run_python_script` | `ideaswork runtime python --workspace <workspace_dir> --script <相对script_path> --args-json @args.json --json` |
| 脚本内 `call_platform_api` | Runtime Core 父进程 bridge；不得裸跑脚本或把 OAuth/lease 传给子进程 |
| `sandbox_bash` | Host Shell，在实际 Skill workspace 执行；不是平台 sandbox |
| `register_async_poll` | `ideaswork runtime wait-result`；不自行 sleep/轮询、不等待平台回调 |
| `ask_user_interact` | Agent 在当前对话中收集同一字段、默认值与确认；不要求 TTY，不代替用户答题 |
| 素材候选 | `ideaswork material list --query "..." --json`；用户确认服务返回的素材，不能猜 URL/ID |
| 成果预览 | 宿主支持的媒体展示或产物地址；不承诺 MCP App 卡片 |

表中每个 CLI 命令都必须复用同一 `--task`。API code 和参数来自当前授权文档。
Batch 仅用于已查询文档、彼此独立的调用；不要为省命令把有数据依赖的步骤合并。
`need_user_approval` API 仍受远端拒绝规则约束；聊天确认不替代正式审批。

## 等待与恢复

先根据创建响应的真实任务 ID、状态查询文档和 `wait_result_hint` 组织查询条件。
完成条件沿用 Runtime Core schema，例如 `{"field":"data.status","value":"succeeded"}`；字段以文档为准。
按 Skill 原语或 hint 查不到结果时，改用 `task_status`（`task_id` 取创建响应的真实任务 ID）尝试。

```bash
ideaswork runtime wait-result --query-api-code <query_code> \
  --params-json @query.json --completion-json @completion.json \
  --initial-delay 5 --interval 10 --max-polls 30 \
  --state-file <任务目录>/wait.json --progress --json --task <task>

ideaswork runtime wait-result --tasks-json @tasks.json \
  --completion-policy all --state-file <任务目录>/batch-wait.json \
  --progress --json --task <task>

ideaswork runtime wait-result --resume <任务目录>/wait.json --json --task <task>
```

`tasks.json` 是非空数组，每项包含 `key / query_api_code / query_params / completion_config`。
策略支持 `all / any / cnt:N`。完成规则可加 `fail_if` 子条件（同样的 field/op/value schema），
只按状态 API 文档中的失败终态判断失败，不猜字段。同批任务用一个等待进程；已完成项在续等时跳过。
`--state-file` 是显式本地持久化，仅保存查询参数、任务结果和绑定摘要，不保存 OAuth/lease。
查询参数也可能包含业务隐私，应保留在任务私有目录，勿提交。已有状态文件用 `--resume`，不覆盖。

- 退出 `3`：本段等待超时，远端任务不一定失败；续等，不重提交创建请求。
- 退出 `130`：本地被中断，远端任务不一定取消；状态已保存时可以续等。
- `mcp_context_lost`：旧 Context/grant 可能已丢失。先查询当前 Context，用户核对工作区，再重新
  pull 原 Skill、查询文档；不重放可能有副作用的 Python/API。旧等待文件因平台会话变化可能拒绝自动续等，
  此时先核对原任务真实状态，再在正确授权 Context 中用原任务 ID 新建等待定义，不能新建生成任务。
- `request_outcome_unknown`：请求可能已执行；先核对远端状态，不盲目重试。
- `wait_state_mismatch / wait_context_mismatch`：身份、task 或平台会话不同；不在新项目自动续等。

Runtime 等待不等于后台唤醒 Agent。Harness 要保持命令执行或提供自己的续接机制；不承诺自动恢复对话。
