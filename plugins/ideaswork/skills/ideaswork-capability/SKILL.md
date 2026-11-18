---
name: ideaswork-capability
description: 通过 IdeasWork Remote MCP 查询、调用和组合平台业务能力，完成生成、处理、查询等实际任务。用户尚未要求构建 Skill 时，即使连续使用多个 API 也保持此工作流；明确要把已有成果沉淀为 Skill 时交给 ideaswork-builder，查找或运行已发布 Skill 时交给 ideaswork-runner。
---

# IdeasWork Capability

## 执行入口（Plugin：只有 Remote MCP）

本制品的平台能力、Catalog、Context、表单、异步查询都走 Remote MCP 工具。没有 `ideaswork` 命令、npm 或独立 CLI，
不要寻找或安装它们。连接缺失时按下文恢复，不因工具暂未注入而换身份，不用裸 HTTP 冒充 MCP。

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
| 5 | `blue_exec_api` | 异步时下一步查状态，同步 API 无后续 |
| 6 | `blue_exec_api` 反复查状态 API | 同步 API 无此步 |

规则：

- **互不依赖的调用放在同一轮发出**（如两个 `blue_query_api_docs`，或创建 API 与其状态 API 的文档查询）。
  宿主若串行执行也无妨，仍少一次模型往返。有数据依赖的不得同轮：`exec` 依赖文档，状态查询依赖任务 ID。
- **lease 不是调用 `blue_*` 或 `ask_user_interact` 的前置条件**：它们走宿主 OAuth，异步状态查询也是。
  本制品里只有**本地文件上传**需要 lease（见文末「本地素材上传」）。不要预先取；在确定要上传本地文件的那一轮再
  `create_runtime_lease`，并在有效期内复用。
- 用户原话和 API 文档默认值能确定的参数不要再问；必须问时一次问全（见「MCP Apps」）。
- 互相独立、文档均已查询的多个操作，用一次 `blue_exec_api`（传 `calls` 批量），不拆成多轮单调用。

## 工作区边界（默认不切换）

默认只在**当前工作区**里工作：有 active Context 就用它，没有就用登录时的 OAuth 默认团队/项目。

- **不得自行更换团队或项目。** 找不到 Skill、API 没权限、素材不在这里、想“试试别的项目”，都不构成理由：如实告诉用户，
  问他是否要换，不要自己去 `browse_contexts` / `context list` 找出路。
- **只有两种情况会切换**：① 用户在本轮明确要求切换（点名了团队/项目）；② 当前工作区确实无法继续（默认项目缺失或不可访问、
  服务端明确要求选择工作区、原 Context 丢失需要恢复）。第②种必须**先停下**，说明原因并列出本次候选，等用户明确同意；
  不得静默切换，不得替用户猜选，不得回落到 OAuth 默认项目冒充恢复。
- **切换前把“从 A → 到 B”（团队/项目名称）告诉用户并得到同意**。一次同意只对应这一次切换；之后要回原工作区同样要问。
  切换后用 `get_current_context` 再确认一次当前工作区。
- **不算切换、无需询问**：省略 `context_ref` 初始化 Context、只切 mode、复用当前会话。
- MCP 的 `switch_context(context_ref=…)` 服务端目前不强制确认，所以更要自觉遵守本节：切换前必须先问用户。

## 连接与上下文

1. 先检查本 task 是否已有 IdeasWork Remote MCP 工具（例如 `get_current_context`、`blue_query_api_docs`）。
   - 若没有：请用户在插件中完成/重新触发 **Connect IdeasWork** 的 OAuth 授权，然后重连或新建 task。
   - 不执行 `codex mcp login`，不以 `List MCP resources` 是否为空判断登录或工具可用性。
2. **上下文只确认一次**：本会话内任一 `get_current_context` / `switch_context` 的返回已显示 capability 模式的
   active context，且用户没有要求换工作区，就直接进入「调用能力」，不重复检查。否则调用 `get_current_context`；
   没有 active context 或当前 mode 不是 `capability` 时调用：
   ```text
   switch_context(mode="capability")
   ```
   不传 `context_ref` 时服务端使用 OAuth 默认团队和项目。
3. 用户要更换团队或项目时（见上文「工作区边界」：先把“从 A → 到 B”告诉用户并得到同意），调用 `browse_contexts` 获取当前最新候选；不要依赖 MCP App 展开卡片或旧的
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
   汇报尚未开放，不通过切 mode、拉不相关 Skill、本地脚本或裸 HTTP 绕过；Runtime lease 不扩大权限。
4. 只有多个操作彼此独立、每项文档均已查询、且不需要逐项根据结果调整时才用 `blue_exec_api` 的 `calls` 批量。否则按顺序
   调用 `blue_exec_api`。
5. 若返回异步任务 ID，用 `blue_exec_api` 反复调用状态查询 API 取得结果。这条路径走宿主 OAuth，**不用 lease、不占 lease 额度**；
   **提交成功不等于完成**，不要把"请求已提交"当作最终结果。
   - 优先用创建响应里的 `wait_result_hint`：`query_api_code`（状态查询 API）与 `completion_config`（完成条件）；
     其文档若还没查过就先 `blue_query_api_docs`；查询参数从创建响应里的**真实任务 ID** 组织。
   - hint 带 `fallback` 时，主查询查不到就用它；缺少查询 API，或 hint 的查询 API 查不到结果（如 Remote MCP 下
     `t2v_session_task_create` 的 `t2v_session_task_query` 按会话恒为空，应用 `data.data.base_task_id` 查 `task_status`）时，
     仅在 `task_status` 已授权且文档确认适用时使用它。`task_status` 不返回 `cdn_url`，需要时再查 `task_detail`。
   - **判定规则**按 `completion_config` 逐字执行：`field` 是 `.` 分隔的路径（不含 `[]`）；`op` 默认 `eq`，支持
     `eq / ne / in / not_in / contains / exists / gt / gte / lt / lte`；`all_of` / `any_of` 是规则数组；`fail_if` 命中即判**失败**，
     优先于成功判定；字段不存在视为"还没完成"，除非规则用了 `exists`；不能拿传输层的 `code` / `status` / `message` 当完成字段。
   - **轮询**：同批互相独立的任务合并进**一次** `blue_exec_api(calls=[…])` 查询，已到终态的不再查；两次查询之间用 Host Bash
     `sleep <秒>`（首次可先 `sleep 30`，之后约 15 秒）。一段等待窗口给总次数设上限（例如 20 次），到上限仍未终态就如实汇报
     任务 ID 与"仍在生成"，由用户决定是否继续；**不重新提交创建请求**，创建过的任务只查询、不重建。
   - 无授权、无状态接口或到上限时，汇报任务 ID 和实际状态，不绕过服务端准入，不猜测参数或结果字段。
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
  不把聊天确认当成审批，不用其他路径绕过。
- MCP App 无法渲染时，才在文本中收集同一字段；无需提交/状态工具。

## 汇报

简洁说明：使用的能力、实际结果/产物、仍在进行的任务、以及需要用户补充或确认的事项。失败时说明服务端返回的
可操作错误；不要伪造结果或反复重试同一失败请求。

## 本地素材上传

- 用户指定本地文件、或需要将本地产物入素材库时，复用 `material_upload_proxy`。
  先确认当前 Context 和 API 文档/grant（先 `blue_query_api_docs("material_upload_proxy")`），
  不能把本机文件路径直接发给 `blue_exec_api`。
- 这是本制品里**唯一需要 lease** 的动作：调用 `create_runtime_lease`（或沿用 `pull_skill` 返回的 lease）取得
  `material_upload_endpoint` 与 `runtime_lease`。lease **只经 stdin 传给 curl**（`-H @-`），不写进命令行参数、环境变量、文件或日志：

  ```sh
  curl -fsS -X POST -H @- --max-time 900 \
    -F 'body={"<API 文档要求的其它参数>":"..."}' \
    -F 'file=@<本机文件路径>' \
    "<material_upload_endpoint>" <<'EOF'
  Authorization: Bearer <runtime_lease>
  EOF
  ```

  `body` 是不含 `file` 的 JSON 对象（至多 64 KiB），`file` 恰好一个、非空、至多 500 MiB；两个字段都要有，不要再加别的字段。
  上传前确认路径是普通文件（不是软链）。需要 `curl`（macOS / Linux / WSL）；原生 Windows 不在本制品支持范围，如实告知用户。
- lease 缺失/过期：通过当前 MCP 获取新的 lease；Context 改变先确认 Context。不因权限拒绝切换入口。
- **超时或结果未知不自动重传**：Engine 的 MD5 复用不保证素材创建幂等，重传可能重复创建素材。先检查素材库再决定。
- 上传返回 `material_id` 后，后续 API 里只传 `material_id`，不再补一次上传。
