# 平台能力使用与组合的 CLI 绑定

CLI 型制品或用户明确选择独立 CLI 时，使用以下链路，替代 Remote MCP 工具/App/lease 指引。
权限仍由同一远端服务强制执行，不用旧 Local MCP、`local_rpc`、裸 HTTP 或其他登录身份绕过。

一次简单任务常见只需：`context` →（必要时 `context use`）→ `api list` → `api docs` → `api exec` → `runtime wait-result`。
CLI 在 `wait-result` 内部自己取 lease，没有单独的 lease 步骤；互不依赖的命令（如创建 API 与其状态 API 的 `api docs`）
放在同一轮发出。

1. 固定本地 `--task <task>`（不是平台 session ID），后续所有命令和切换工作目录后均复用。
   CLI 默认按 cwd 隔离；同目录并行任务必须不同 task。**直接**运行 `ideaswork context --json --task <task>`：
   它既查看 Context，也是认证探针——未登录时返回 `not_authenticated / next_action=login`，此时请用户完成
   `ideaswork login`。不必先跑 `doctor`；`doctor --json` 只在连通性或安装异常需要诊断时使用。
   正式制品环境由渠道固定，不支持 `--env`。
2. 本会话已确认 capability Context 且工作区未变，就不再检查。无 active 或 mode 不符时执行
   `ideaswork context use --mode capability --reuse-session --json --task <task>`，保留当前/使用 OAuth 默认项目。
   **默认不切换工作区。** 要换工作区，先 `context list`，把候选和“从 A → 到 B”展示给用户并得到同意，再传本次 `context_ref`
   并加 `--confirm-switch`（不带会被拒绝，不得为让命令通过自行添加；找不到 API/权限不足不是切换的理由）。
3. `ideaswork api list --json --task <task>` 仅列当前已授权 API，不是全量注册表；已知关键词时加 `--query "<词>"`
   在本地过滤，缩小输出。已知 `api_code` 或同一 Context 内已列过就不重复 list。
   `ideaswork api docs <code> --json --task <task>` 查询 schema（同一 Context 内已查过的 code 不重复查），再用
   `ideaswork api exec <code> --body @body.json --json --task <task>` 执行。
   普通开放 API 无需先 pull Skill；垂类（DB category 以 VERTICAL 开头）和策略 API 不直接开放。
   实际可用范围以服务端为准；旧部署返回小名单限制时如实报告，不切身份、拉不相关 Skill 或改调用入口绕过。
   执行已发布 Skill 用 Runner；仅用户明确要求沉淀已有流程或创建 Skill 时进入 Builder，承接真实结果不重跑。
4. 缺失参数优先由用户原话和 API 文档默认值确定；仍缺的在对话中一次问全。素材候选用
   `ideaswork material list --json --task <task>`，等用户确认再采用真实 ID/URL。不依赖交互式 TTY，
   不替用户做素材或规格选择。正式审批仍按服务端限制；聊天确认不是审批凭证。
5. 异步任务用 Runtime Core 的 CLI 入口：
   `ideaswork runtime wait-result --query-api-code <状态API> --params-json @query.json --completion-json @completion.json --state-file <任务目录>/wait.json --progress --json --task <task>`。
   多任务改用 `--tasks-json @tasks.json`，每项包含 `key / query_api_code / query_params / completion_config`。
   超时退出 3，续等用 `--resume <原文件>`；不再次提交生成。中断 130 不代表取消远端任务。
6. 读取 `error_code / next_action`。Context 丢失时重新核对工作区和文档；等待文件与平台会话不一致时
   先核对原任务状态，再在正确授权 Context 用原任务 ID 创建新的等待定义。
   网络结果不明时不自动重放；没有授权/状态接口时报告实际限制。
7. 用宿主媒体展示或产物地址汇报实际结果，不把已提交说成已完成，不承诺完成后自动唤醒对话。

`--json` 成功保留业务 payload；失败结构化。状态文件不存 OAuth/lease，但可能含业务隐私，保留本地不要提交。
