# Builder 的 CLI 执行绑定

CLI 型制品、Shell Harness 或明确的独立 CLI 任务使用本节。它只替换执行入口，不改变
conversion/sampling 模式、渐进加载、用户授权、API grant 或 draft/publish 边界。

- 使用 PATH `ideaswork` 或制品随包入口，固定 `--task <task>` 并在后续命令和 workspace 切换后复用。
  同目录并行任务必须不同 task；task 不是平台 session ID。`doctor --json` 检查状态，未登录时
  请用户完成独立 CLI OAuth。不能读取 Plugin token；Plugin 已授权不等于 CLI 已登录。
- 本地编写、`skill validate` 和 `skill gaps` 不要求先登录、建立 builder Context 或拥有 write。
  从已有成果沉淀时复用需求/证据，仍按 conversion/sampling 阶段推进，不重跑已成功的昂贵步骤。
- 远端动作先复用当前有效工作区，**默认不切换**；需要换工作区才 `context list --json`，把“从 A → 到 B”告诉用户并得到同意，
  再 `context use <ref> --confirm-switch`（不带会被拒绝，Agent 不得自行添加）。
  只有动作要求 builder mode 时才 `context use --mode builder`；同工作区可省略 ref 并使用 `--reuse-session`。
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
- 本地编辑、`skill validate`、`skill gaps` 沿用各阶段规则；`skill push` 在上传前会先跑与服务端相同的校验（SKILL.md、api.json、`skill_sop.json` 结构，
  名称/版本号/分类格式，100 MiB 解压上限），不通过时返回 `validation_failed`（退出码 1）且不上传，按提示修好草稿再推。`skill push <draft> --name <name> --json`（给已有 Skill 加版本用
  `--skill-id <id>`）只在用户明确要求提交时运行，未被要求就不运行、不提及。它不再走 `push_skill` 工具，而是先本地打包校验，
  再用自己的 OAuth 取 Runtime lease 做 HTTP 上传；沿用已有 Context，没有 active context 才切到 `builder`。lease 载荷没有
  `skill_push_endpoint` 时返回 `tool_unavailable / keep_local_draft` 且不上传，此时保留草稿并如实说明，不记 gaps、不重试。
  结果是待审核版本（pending），不是 draft，也不是 publish，属主在 Studio 版本历史接受后才生效。
  `--set-current`、`--visibility` 默认不传，**不得主动添加**，先在对话里问用户；`--visibility` 只用于新建（`private` 或 `team`），
  更新已有 Skill 不加。网络中断或网关 5xx 后返回 `push_result_unknown`（退出码 6）不自动重试，先让用户在「我的 Skill」或
  版本历史确认。连接建立前就失败（沙箱断网、域名解析失败、连接被拒）返回 `push_network_unreachable`（退出码 1，`retryable=true`）：
  请求没有发出，草稿与线上版本不变，不必查版本历史；向用户说明并申请放开网络权限，放开后再推一次。scope 或业务权限不足同样保留草稿。
  核实一次推送生成了什么：`ideaswork skill versions <skill_id> --json`（只读，仅 OAuth CLI；新建 Skill 不知道 id 时先 `skill list --query <名称>`）。
  CLI 没有接受/回滚/改分享范围的命令，这些在 Skill Studio 或 Plugin 的属主管理工具里做。
  Plugin 任务不能自动转 CLI OAuth 绕过；已具 scope 但业务权限不足不重复 login，按真实拒绝引导申请业务权限。

以上命令均通过 `ideaswork` 调用并复用原 `--task`。`--json` 成功保留业务 payload，失败带
`error_code / next_action / retryable`。状态文件不存凭证但可能有业务隐私，勿提交。
`runtime python` 在所有平台都需要本机 Python 3.10+（macOS 自带的 `/usr/bin/python3` 是 3.9，不能用）。版本不够时返回
`python_version_unsupported`（退出码 2），脚本不会执行：把消息里的解释器路径和版本告诉用户，请用户装 3.10+ 后用
`--python-executable` 指定，不要改写脚本去兼容旧版本。Windows 原生可运行 Python bridge，入口用 `.cmd`，JSON 参数用 `@文件`；portable 自更新仍需 WSL；自动唤醒、富交互卡片和新审批通道不在 CLI 能力承诺中。
