# Builder 的 CLI 执行绑定

CLI 型制品、Shell Harness 或明确的独立 CLI 任务使用本节。它只替换执行入口，不改变
conversion/sampling 模式、渐进加载、用户授权、API grant 或 draft/publish 边界。

- 使用 PATH `ideaswork` 或制品随包入口，固定 `--task <task>` 并在后续命令和 workspace 切换后复用。
  同目录并行任务必须不同 task；task 不是平台 session ID。`doctor --json` 检查状态，未登录时
  请用户完成独立 CLI OAuth。不能读取 Plugin token；Plugin 已授权不等于 CLI 已登录。
- 本地编写、`skill validate` 和 `skill gaps` 不要求先登录、建立 builder Context 或拥有 write。
  从已有成果沉淀时复用需求/证据，仍按 conversion/sampling 阶段推进，不重跑已成功的昂贵步骤。
- 远端动作先复用当前有效工作区；需要换工作区才 `context list --json` 并让用户确认。
  只有动作要求 builder mode 时才 `context use <ref> --mode builder`；同工作区可省略 ref 并使用 `--reuse-session`。
  旧部署可能仍创建新平台会话，需保留原任务/结果关联并重新核对 grant/lease。正式 CLI 制品环境由渠道固定，不支持 `--env`。
- 发现已有 Skill 用 `skill list --query "..." --json`；列当前授权 API 用 `api list --json`；
  查询文档用 `api docs <code> --json`。Builder 不隐式继承 capability 或其他 Skill grant，
  不可见不等于平台未注册。需要按既有发现规则切 mode/查看 Skill 时仍须核对工作区和授权范围。
- API 调用用 `api exec <code> --body @body.json --json`；仅彼此独立且已查文档的调用用
  `api batch --calls-json @calls.json --json`。昂贵、批量、发布、删除操作仍按 Builder 授权规则确认。
- Python 验证用 `runtime python --workspace <cwd> --script <相对路径> --args-json @args.json --json`，
  通过 Runtime Core bridge 保留 `call_platform_api`。不裸跑、不把 OAuth/lease 下发给子进程。
- Bash 用 Host Shell，在实际 workspace 执行。需求/素材选择用对话和 `material list --json`，
  不替用户答题或把聊天确认当正式审批。
- 异步任务用 `runtime wait-result` 的 `--query-api-code / --params-json / --completion-json`，
  多任务用 `--tasks-json`；可显式 `--state-file`，超时退出 3 后 `--resume <文件>`，不重复创建任务。
  中断/网络结果不明/Context 丢失先核对实际状态，不盲目重跑有副作用的验证脚本。
- 本地编辑、`skill validate`、`skill gaps` 沿用各阶段规则。`skill push <draft> --name <name> --json` 只在用户明确要求提交时运行，
  未被要求就不运行、不提及；它只创建 draft，不是 publish。它先本地打包校验再探测 `push_skill`，探测不到返回
  `tool_unavailable / keep_local_draft` 且不改动 Context，此时保留草稿并如实说明，不记 gaps、不重试。scope 或业务权限不足同样保留草稿。
  Plugin 任务不能自动转 CLI OAuth 绕过；已具 scope 但业务权限不足不重复 login，按真实拒绝引导申请业务权限。

以上命令均通过 `ideaswork` 调用并复用原 `--task`。`--json` 成功保留业务 payload，失败带
`error_code / next_action / retryable`。状态文件不存凭证但可能有业务隐私，勿提交。
Windows 原生可运行 Python bridge（本机需 Python 3.10+），入口用 `.cmd`，JSON 参数用 `@文件`；portable 自更新仍需 WSL；自动唤醒、富交互卡片和新审批通道不在 CLI 能力承诺中。
