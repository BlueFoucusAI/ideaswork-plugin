---
name: ideaswork-capability
description: 通过 IdeasWork Remote MCP 或独立 CLI 查询、调用和组合平台业务能力，完成生成、处理、查询等实际任务。用户尚未要求构建 Skill 时，即使连续使用多个 API 也保持此工作流；明确要把已有成果沉淀为 Skill 时交给 ideaswork-builder，查找或运行已发布 Skill 时交给 ideaswork-runner。
---

# IdeasWork Capability

> 本制品不内置原生程序：首次需要本地 Runtime Core 命令前，先读 [references/PLUGIN_RUNTIME.md](references/PLUGIN_RUNTIME.md) 检查并按指引安装。

## 执行入口选择（先于后续工具指引）

- 制品明确为 `cli`、用户明确使用独立 CLI，或当前是仅提供 Shell/文件读写且没有原生 IdeasWork MCP 的
  Harness：先读 [references/CLI_BINDING.md](references/CLI_BINDING.md)，使用 CLI 绑定。
  该绑定替代后文 Remote MCP/App/lease 的调用方式，但不改变业务 Skill、用户授权或服务端权限边界。
- 已配置 Remote MCP 的制品/任务：沿用下文 Remote MCP 主链路。连接缺失时按插件连接指引恢复，
  不因工具暂未注入自动切换 CLI 身份，不把 CLI 当作权限或审批失败的绕过通道。


在不运行完整线上 Skill 的情况下，查询、调用或组合 IdeasWork 的**平台业务能力**完成用户目标，不要求先构建 Skill：

```text
确认上下文 → 发现能力并查询 API 文档 → 收集缺失需求 → 调用/组合 API → 汇报结果
```

## 路由边界

- 用户问“有哪些 Skill”、找/推荐/拉取/运行已发布 Skill：交给 `ideaswork-runner`，从 `browse_skills` 开始。
- 用户明确要把刚才的流程/成果做成可复用 Skill，或明确要构建、转化 Skill：交给 `ideaswork-builder`。
- 用户要直接生成、处理、查询或组合能力完成任务：使用本 Skill；连续调用多个 API 不等于在打样 Skill。
- 三个指引不是用户角色，可以按意图连续衔接，无需换包、换账号或重选角色。保留已确认的工作区、需求、素材、
  参数调整和结果；不要自动触发 Builder，不在切换指引时重跑此前任务。
- 用户要求沉淀时，把真实 API 调用顺序、参数来源、成功/失败证据、任务 ID 和产物引用交给 Builder。
  当前上下文或已有文件足够时直接复用；平台历史读取只使用实际提供且获授权的入口，不臆造查询工具。
- 不把当前插件内的 Runner、Builder 或本地文件当作平台能力或线上 Skill Catalog。

## 最短路径（Remote MCP）

一次简单任务（例如生成一个视频）常见只需 4–6 轮；不要为“稳妥”多走步骤：

| 轮 | 动作 | 何时可省或合并 |
|---|---|---|
| 1 | `get_current_context` | 本会话已见 `active_context.mode == "capability"` 且工作区未变：跳过 |
| 2 | `switch_context(mode="capability")` | 仅无 active context 或 mode 不符时 |
| 3 | `blue_list_apis` | 本 Context 内已列过，或 `api_code` 已由前文确定：跳过 |
| 4 | `blue_query_api_docs`：创建 API，**连同**已知的状态查询 API | 同一 Context 内已查过的 `api_code` 不重复查 |
| 5 | `blue_exec_api`；已确定是异步时，**同一轮**加 `create_runtime_lease` | 同步 API 无需 lease |
| 6 | `sh <plugin_root>/runtime/bin/ideaswork runtime wait-result` | 同步 API 无此步 |

规则：

- **互不依赖的调用放在同一轮发出**（如两个 `blue_query_api_docs`，或异步创建与 `create_runtime_lease`）。
  宿主若串行执行也无妨，仍少一次模型往返。有数据依赖的不得同轮：`exec` 依赖文档，`wait-result` 依赖任务 ID。
- **lease 不是调用 `blue_*` 或 `ask_user_interact` 的前置条件**：它们走宿主 OAuth。只有本地 Runtime Core 动作
  （`wait-result`、`runtime python`、素材上传）才需要 lease。不要在 `get_current_context` / `switch_context` 之后预先取；
  在确定要做本地动作的那一轮取，并在有效期内复用。
- 用户原话和 API 文档默认值能确定的参数不要再问；必须问时一次问全（见「MCP Apps」）。
- 互相独立、文档均已查询的多个操作，用一次 `blue_exec_batch`，不拆成多轮单调用。

## 连接与上下文

1. 先检查本 task 是否已有 IdeasWork Remote MCP 工具（例如 `get_current_context`、`blue_query_api_docs`）。
   - 若没有：请用户在插件中完成/重新触发 **Connect IdeasWork** 的 OAuth 授权，然后重连或新建 task。
   - 不执行 `codex mcp login`，不读取 CLI 登录态，不以 `List MCP resources` 是否为空判断登录或工具可用性。
2. **上下文只确认一次**：本会话内任一 `get_current_context` / `switch_context` 的返回已显示 capability 模式的
   active context，且用户没有要求换工作区，就直接进入「调用能力」，不重复检查。否则调用 `get_current_context`；
   没有 active context 或当前 mode 不是 `capability` 时调用：
   ```text
   switch_context(mode="capability")
   ```
   不传 `context_ref` 时服务端使用 OAuth 默认团队和项目。
3. 用户要更换团队或项目时，调用 `browse_contexts` 获取当前最新候选；不要依赖 MCP App 展开卡片或旧的
   `context_ref`。用本次结果中的名称通过 `ask_user_interact` 的 `select` 让用户明确选择，结束本轮等待提交，
   再将该选项对应的本次 `context_ref` 传给 `switch_context(context_ref=..., mode="capability")`。
4. 仅当用户明确要新建平台会话、或需要隔离一项新工作时传 `new_session=true`。普通连续调用不得新开会话。
   不构造 `context_ref` 或 `avp_session_id`。

## 调用能力

1. 根据用户目标用 `blue_list_apis` 发现当前可用 API，再确定调用和数据流；列表只提供能力摘要，不替代文档。
   不确定 API、参数或能力边界时，先问必要问题或用表单收集信息，不能猜测 `api_code`。
2. 对每一个要调用的 `api_code`，先调用：
   ```text
   blue_query_api_docs(api_code)
   ```
   只使用返回的 schema、必填参数、限制与结果说明组织 body。同一 Context 内已成功查过的 `api_code` 不重复查；
   Context 变化（含 `new_session`），或 `blue_exec_api` 因未查文档被拒绝时再查。
   若创建 API 的文档或 `blue_list_apis` 结果已指明其状态查询 API，与创建 API 的文档**同一轮**一并查询。
3. 再调用：
   ```text
   blue_exec_api(api_code, body)
   ```
   不维护本地 API code 小名单。目标准入为：普通开放业务 API 可直接使用；垂类 API（服务端 DB 的 `category`
   以 `VERTICAL` 开头）和带服务端策略标识的 API 不在 Capability 中直接开放。API 类型与可用范围以服务端为准，
   不靠 `api_code` 名称猜分类、不要求为普通 API 先 pull 一个 Skill。
   服务端仍校验 scope、工作区/资源权限、额度、依赖和审批。若旧部署仍返回 allowlist/grant 限制，以真实拒绝为准，
   汇报尚未开放，不通过切 mode、拉不相关 Skill、本地脚本、CLI 或裸 HTTP 绕过；Runtime lease 不扩大权限。
4. 只有多个操作彼此独立、每项文档均已查询、且不需要逐项根据结果调整时才用 `blue_exec_batch`。否则按顺序
   调用 `blue_exec_api`。
5. 若返回异步任务 ID，统一使用本地 Runtime Core `sh <plugin_root>/runtime/bin/ideaswork runtime wait-result` 等待并获取结果。
   使用 `wait_result_hint` 的查询 API 和完成条件；其文档若还没查询过就先查，按创建响应中的真实任务 ID
   组织查询参数；缺少查询 API，或 hint 的查询 API 查不到结果（如 Remote MCP 下 `t2v_session_task_create`
的 `t2v_session_task_query` 按会话恒为空，应用 `data.data.base_task_id` 查 `task_status`）时，
仅在 `task_status` 已授权且文档确认适用时使用它。
   需要 lease 时调用 `create_runtime_lease` 取得当前 capability Context 的短期 lease（已确定是异步时可与
   `blue_exec_api` 同轮发出），有效期间串行复用；
   把 `runtime_endpoint` / `runtime_lease` 仅传给 Runtime Core parent，不写入文件或普通日志。
   单任务传 `--query-api-code / --params-json / --completion-json`；同批多任务一次传 `--tasks-json`。
   用等待器的 `--initial-delay / --interval / --max-polls` 管理等待窗口，不由 Agent 手工 sleep 或轮询。
   `timeout` 只表示本段未完成；任务仍在运行时续等，不重提交创建请求。lease 失效后按返回的
   `next_action` 重签或核对 Context，再继续等待。无授权、无状态接口或等待到上限时，汇报任务 ID
   和实际状态，不绕过服务端准入，不猜测参数或结果字段。
6. 结果中的任务标识、产物地址、错误或后续动作必须如实汇报；不要将“请求已提交”表述为“已生成完成”。

## MCP Apps：需求与素材

- 用户意图和参数已经足够明确时，不必额外弹表单。
- **调用 `ask_user_interact` 前先读 [references/FORMS.md](references/FORMS.md)**：照其中的骨架、字段类型表和 few-shot
  写参数，过一遍提交前自检。`tabs` 必须是数组对象；字段只用文档列出的键和 10 种类型；`select` 的 `options`
  是 `{label, value}` 对象数组；默认值写 `value`；数字、布尔、数组不要写成字符串。
- 缺少多个结构化字段、需要选择规格或让用户确认可变选项时，调用**一次** `ask_user_interact`，把缺的字段和素材字段一次问全。
  展示后结束本轮，等用户的普通消息回传 `interaction_response`；核对 `interaction_id`、`action` 和 `data`，
  确认后直接继续，取消则停止相应动作。没有 `submit_interaction` / `get_interaction_status` 工具，不猜测或代替用户选择。
- 需要用户从素材库选素材时，先确认当前已绑定工作区，调用 `ask_user_interact` 并加入
  `{"key":"material","type":"built_in","component":"material_picker","label":"素材","accept":["image"],"multi":false}`
  等素材字段；表单内二级展开素材库，所选对象随 `interaction_response.data` 回传。`browse_materials` 只是
  表单 App 的只读取数工具，不直接渲染选择器。仅当表单发出 `material_pick_request`（宿主不支持 App 内
  取数）时，Agent 才用 `browse_materials` 在对话中列候选；用户文字确认后将素材写入字段 `value`，用
  `draft` 回填其他字段，再展示表单。
- Remote MCP 没有审批通道：`blue_exec_api` 对 `need_user_approval` API 会拒绝执行。告知用户限制并停止，
  不把聊天确认当成审批，不用 CLI 或其他路径绕过。
- MCP App 无法渲染时，才在文本中收集同一字段；无需提交/状态工具。

## 汇报

简洁说明：使用的能力、实际结果/产物、仍在进行的任务、以及需要用户补充或确认的事项。失败时说明服务端返回的
可操作错误；不要伪造结果或反复重试同一失败请求。

## 本地素材上传

- 用户指定本地文件、或 Skill 需要将本地产物入素材库时，复用 `material_upload_proxy`。
  先确认当前 Context 和 API 文档/grant，不能把本机文件路径直接发给 `blue_exec_api`。
- Remote MCP 模式：从当前 MCP 的 `create_runtime_lease`（或 pull 返回）取得 lease，
  使用随包 `runtime/bin/ideaswork material upload <文件> --runtime-endpoint <地址>
  --runtime-lease-stdin --json`；lease 经 stdin 或父进程环境传入，不写入文件/日志，
  不要求独立 CLI 登录。
- 显式 lease 缺失/过期：通过当前 MCP 获取新的 lease；Context 改变先确认 Context。
  不自动改用 CLI 自己的账号，也不因权限拒绝切换入口。
- 独立 CLI 模式：`ideaswork material upload <文件> --json` 使用 CLI 自己已有登录和
  task Context，内部获取 lease。复用同一 `--task`，不自动选择项目或扩展 grant。
- Runtime 执行 Skill 脚本时，原 `__call_platform_api_file:<workspace相对路径>` 写法
  保留；父进程负责上传，子进程不接收 lease。上传返回 material_id，不再补一次上传 API。
- 超时/结果未知不自动重传，先检查素材库，避免重复创建素材。
