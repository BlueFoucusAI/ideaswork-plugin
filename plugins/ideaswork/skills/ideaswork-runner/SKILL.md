---
name: ideaswork-runner
description: IdeasWork（心影）线上已发布 Skill 的**首要发现与运行入口**。用户通过 IdeasWork 询问「有什么/有哪些/可用哪些/找一下/搜索/推荐 skill」「心影有哪些 skill」「帮我找个 skill」时，默认指**远端已发布 Skill Catalog**，必须先查询远端 Catalog：原生 MCP 走 `browse_skills`，CLI 走 `ideaswork skill list`，不能把当前工作区、Codex 已安装 Skill、插件 Runner/Builder 说明或本地文件误当答案。仅当用户明确说「本地/已安装/Codex/工作区 skill」时才讨论本地 Skill。也用于拉取、运行或验证已发布心影 Skill；设计、转化、打样、发布 Skill 属于 ideaswork-builder。
---

# IdeasWork Runner

> 本制品不内置原生程序：首次需要本地 Runtime Core 命令前，先读 [references/PLUGIN_RUNTIME.md](references/PLUGIN_RUNTIME.md) 检查并按指引安装；Windows 原生环境用其中的 `.cmd` 写法，不要用 `sh`。

## 执行入口选择（先于后续工具指引）

- 制品明确为 `cli`、用户明确使用独立 CLI，或当前是仅提供 Shell/文件读写且没有原生 IdeasWork MCP 的
  Harness：先读 [references/CLI_BINDING.md](references/CLI_BINDING.md)，使用 CLI 绑定。
  该绑定替代后文 Remote MCP/App/lease 的调用方式，但不改变业务 Skill、用户授权或服务端权限边界。
- 已配置 Remote MCP 的制品/任务：沿用下文 Remote MCP 主链路。连接缺失时按插件连接指引恢复，
  不因工具暂未注入自动切换 CLI 身份，不把 CLI 当作权限或审批失败的绕过通道。


把一个**已发布**的线上 Skill 拉到本地，优先按它自己的指引和 `api.json` 跑完。
不在 immutable checkout 上直接修改业务指引。用户明确要修改、转化或把执行成果沉淀成新 Skill 时，
衔接 `ideaswork-builder` 并使用独立草稿；直接使用/组合能力时可衔接 `ideaswork-capability`。
三个指引不是账号角色，不要求换包或重新登录；交接保留已确认的工作区、素材、参数、任务 ID 与真实结果。
连续调用多个 API 不自动进入 Builder。

## API 范围：默认聚焦与远端准入分开

- 优先展示和使用主 Skill 及 linked Skills 的 `api.json`；这是一份执行声明，不是用户身份的权限来源。
- **有效 checkout grant 内的 API 可进入后续执行检查，包括垂类和策略 API**；不能先全局排除这些分类再检查 grant。
- 声明外的普通开放 API 可用于当前用户目标的合理补充，先通过实际可用的发现入口定位，再查文档、执行。
  不要求为了普通 API 退出 Runner，不扩大用户目标，不自动修改 `api.json`；真实补充调用留作后续完善 Skill 的证据。
- 声明外的垂类 API（服务端 DB category 以 `VERTICAL` 开头）或带策略标识的 API，必须获当前有效 checkout grant
  授权，否则拒绝。不能靠本地编辑 `api.json`、知道 code 或换工作流获得授权。
- 分类、grant 和资源权限由服务端校验，列表是否可见不等于获得执行授权。旧部署若仍硬限制所有声明外调用，
  如实说明远端尚未开放；不换身份、改入口或切 mode 绕过，也不猜全量 API 查询工具/参数。
- 运行已授权 Skill 不要求 `ideaswork.skill.write`；写入授权用于远端提交/修改，且不替代业务写入权限。

## 术语（全文按此理解，不要另造解释）

- **主 Skill**：你 `pull` 的那个技能；运行目录以 pull 的返回值为准（CLI 会增加 task 子目录）。
- **linked 子技能**：随主 Skill 一起展开的技能，没有自己的 `.avp_run` 目录。
- **平台原语**：查文档 / 调 API / 跑脚本 / 注册异步轮询四类操作（见 §2「MCP 优先」）。

## Skill 语义优先级（先按这里消歧）

当用户是通过 IdeasWork 插件发问，且没有明确加“本地 / 已安装 / Codex / 工作区”限定时，
下面这些说法一律指 **IdeasWork 远端已发布 Skill Catalog**：

```text
有什么 skill / 有哪些 skill / 心影有哪些 skill
找 skill / 搜索 skill / 推荐一个 skill / 可用的 skill
```

处理规则固定为：

1. **先且仅调用一次无参数的 Remote MCP `browse_skills()`**，让 Skill Catalog MCP App 展示远端可用条目。
   不传 `page`、`page_size`、`include_details` 或搜索参数；不要为了“全量”“下一页”“更详细”再次调用。
   Catalog 自己在 App 内完成搜索和分页。调用后立刻结束本轮，等待用户在 App 中选择；不直接在聊天中
   根据模型记忆、Runner/Builder 名称或本地目录手工罗列。
2. `ideaswork-runner`、`ideaswork-builder`、当前 workspace 的 `.claude/skills/`、Codex 已安装 Skill 和
   Plugin 内文件只是**本地指引或宿主能力**，不是“心影有什么 Skill”的默认答案来源。
3. 只有用户明确说“本地 skill”“当前工作区 skill”“Codex 已安装 skill”或给出本地路径时，才切换到本地
   Skill 语义；否则不要把远端 Catalog 问题降级成查本地文件。
4. 若 Remote MCP tools 尚未注入，先按下一节的 OAuth 登录门建立 Codex MCP connection；完成前不要用
   CLI 本地登录态或 `List MCP resources` 代替 Catalog 查询。

## 前置条件（按顺序执行）

### 0. 首次使用的 OAuth 登录门

先检查当前 task 是否已经注入任意一个 IdeasWork Remote MCP tool（例如 `browse_skills`、
`get_current_context` 或 `browse_contexts`）。

- **已经注入**：直接继续下一步。
- **一个都没有**：这是 Codex Plugin 的连接/授权状态，不是让 Agent 在终端代替用户登录的信号。提示用户在
  插件页完成或重新触发 **Connect IdeasWork**；安装策略为 `authentication: "ON_INSTALL"`，Codex 应在安装时
  通过该插件声明的 OAuth-protected Remote MCP 请求用户授权。用户完成浏览器中的登录和授权后，新建或重连
  IdeasWork task，使 Remote MCP tools 与 MCP Apps 注入。

  已安装但仍无工具时，先让用户检查插件连接状态或重新连接；不要执行 `codex mcp login`，不要读取/写入
  CLI OAuth session，也不要用裸 HTTP `/mcp`、本地 token 或 `List MCP resources` 冒充 Codex MCP connection。

> Plugin manifest 只关联 `.mcp.json` 的 Remote MCP；OAuth UI 和 token 由 Codex host 与 MCP 的 protected-resource
> discovery 负责。Runtime Core 不能、也不应读取该 token。

1. **先发现 Remote MCP 工具，再浏览 Catalog**。`browse_skills` 是只读查询：有 active context 时
   使用该团队；没有时使用 OAuth 登录携带的默认团队。它**不创建 AVP session**，列出/搜索 Skill
   时不要先调用 `switch_context`。
2. 用户选定要拉取或运行某个 Skill 后，先读取 `get_current_context`。**初始化 Context 或只切 mode 不等于更换工作区**：
   先检查 `active_context`，为空时读取 `default_context` 的 `team_id` / `project_id`；这是登录时已绑定的工作区。
   `active_context: null` 或 `session.status: "not_started"` 只表示尚未建立运行会话，不表示未绑定工作区；
   返回只有 ID、没有团队/项目名称也不代表绑定缺失。
   - 已有 `skill_runner` Context：直接 `pull_skill`；无需工作区表单，也不重新登录。
   - 没有 active Context 或仅 mode 不符：调用 `switch_context(mode="skill_runner")`，不传 `context_ref`，
     不设 `new_session=true`；由服务端复用当前工作区或使用 OAuth 默认团队/项目。绑定成功后立即 `pull_skill`。
     **不得仅因 `active_context` 为空或 mode 不符就弹工作区选择表单**；使用登录携带的默认值不是从候选列表猜选。
   - 只有用户明确要求换团队/项目，或服务端明确要求选择工作区（默认项目缺失/不可访问）时，才调用
     `browse_contexts` 获取最新候选，再用本次团队/项目名称构造 `ask_user_interact` 的 `select`，
     结束本轮等待提交。只把用户所选项对应的本次 `context_ref` 传给 `switch_context`，不用旧卡片或缓存 ref，
     不替用户猜选其他工作区。其他认证/权限失败按实际错误处理，不把选工作区当作通用修复。
   - 只有用户明确要求新会话才设置 `new_session=true`。若明确报告原 Context 丢失，先恢复原工作区，
     不静默落回 OAuth 默认项目、不重放业务调用。
   `switch_context` 才会绑定 team、project 与隐藏的 AVP session；不要传入或伪造 `avp_session_id`。
   `pull_skill` 返回 immutable checkout archive，由 Host 下载、校验并物化到当前 workspace；
   Codex Plugin 虽随包携带 IdeasWork CLI，主链路不依赖 CLI 或其登录态。
3. `pull_skill` 的返回**自带当前 skill_runner Context 的 runtime lease**（`runtime_endpoint` 与
   `runtime_lease`，随 pull 输出中的 `runtime_lease` 字段下发），后续 Runtime Core 命令直接复用。
   只把它们传给 Runtime Core **parent** 命令，不要写进 Skill 文件、普通日志或传给 Python
   子进程。仅在 lease 失效、额度耗尽或 Context 改变后，才调用 `create_runtime_lease` 重签（有效
   Context 的重复请求会返回同一 lease，**不会延长它的到期时间**）。lease 最长 15 分钟，
   Runtime Core 子进程不能自行续租。以返回的 `expires_in` / `remaining_calls` 判断剩余预算：
   不为「把 600 秒升级为 900 秒」提前重签；若等待可能超过当前剩余有效期，缩短本段
   `wait_result` 的 `max_polls`，待本段完成或 lease 真实失效后再按需重签。新签发时可请求
   最长 900 秒，但 900 秒的参数不改变复用中的 lease。**同一 lease 的 Runtime Core
   调用应串行**，不要用多个并发 `wait_result` 进程轮询同一批任务。不可把租约或其值写入磁盘。
4. 读 [references/EXECUTION_PARITY.md](references/EXECUTION_PARITY.md) 的「能力映射」和
   「已知失真点」两节。本地与平台的全部语义差在那份文件里，本文不重复。

> 所有制品都提供 `ideaswork` 命令作为独立终端入口；它不是 Codex Plugin Runtime 的前置依赖。

本地执行调用**真实平台 API**，会产生费用、数据或项目修改。确认按下面的「授权边界」执行，
不要把正常工作流拆成逐 API、逐素材、逐场景的重复确认。

### 用户授权边界

- 用户明确选择并要求运行一个生成型 Skill（例如「从 0 开始」「继续生成」「按当前方案执行」），视为已授权
  该 Skill **正常主路径**内可合理预期的创建/生成操作，包括按已确认方案批量生图、生音频、生视频和创建
  最终可编辑工程；无需在每个阶段或每个任务前重复询问「是否产生费用」。
- 在展示方案或分镜时，应一次性说明预计会创建的任务数量、主要模型和可预见费用范围；用户确认方案后，
  后续同范围执行直接继续。用户已经在紧邻问题中明确回复「确认 / 继续 / 改吧 / 重生成」时，不再换成表单
  重复确认同一个动作。
- 只有以下情况重新确认：操作超出已确认范围或显著增加成本（新增批次、扩大数量、升级高价模型、第二次及
  后续失败重试）、发布/删除/覆盖等不可逆动作，以及人像协议、隐私或向不同外部目的地分享数据等独立授权。
- 同一批次中的多个同类任务只确认一次；正常预览回传到用户当前正在使用的 IdeasWork App 属于本次运行的
  交付，不再单独询问“是否允许发送预览链接”。

## MCP Apps：优先让用户在界面中选择和确认

Remote MCP 的 MCP Apps 用于 Skill Catalog 和动态表单；素材选择已并入表单。
初始化 Context 或只切 mode 按上节直接使用当前/OAuth 默认工作区，不属于工作区选择交互。
只有需要用户另选工作区时，才用 `browse_contexts` 获取新候选，再通过 `ask_user_interact` 的 `select` 确认；
不使用可能滞后的 MCP App 展开卡片。
App 能完成的筛选或素材选择不要改成模型手写列表；只有明确无法渲染或表单内取数失败时才使用文本 fallback。

| MCP App / 入口 | 用户可完成什么 | Agent 必须怎么做 |
|---|---|---|
| **Skill Catalog**：`browse_skills()` | 浏览当前账号可见的已发布远端 Skill；按**Skill 分类**、名称、来源、状态、描述筛选；本地翻页；选择一个 Skill。分类 chip 是发现 Skill 的首选入口，卡片上的 `category` 是该 Skill 的权威分类。 | 用户问“有什么 Skill”“有哪些分类”“按类别找/推荐 Skill”时，**只调用一次且不传参数**，然后结束本轮等待用户在 Catalog 中按分类或搜索选择。不要手写一份分类/Skill 清单，不要调用 `get_skill_catalog_records`，不要为翻页或换分类再次调用 `browse_skills`。 |
| **工作区切换**：`browse_contexts()` + `ask_user_interact()` | 用户主动换工作区，或默认工作区不可用时另选团队/项目。 | 仅在用户明确要求换团队/项目，或服务端明确要求选择工作区时调用；初始化或仅切 mode 不弹表单。需选择时重新查询，用本次名称构造 `select`，等待提交后传对应的本次 `context_ref`；不使用缓存 ref，也不替用户猜选。 |
| **动态表单（含素材选择）**：`ask_user_interact()` | 填写结构化字段；`built_in` + `material_picker` 字段在表单内二级展开素材库，完成搜索、筛选、翻页和选择。 | 需要素材时先确认 active Context，再把 `accept` 等参数放入素材字段，与其他输入一次收集。调用后结束本轮；用户确认/取消会以 `interaction_response` 普通用户消息回到对话，直接据其 `action` 和 `data` 继续，不调用提交/状态工具。不得猜测用户选择。 |
| **素材库取数**：`browse_materials()` | 为表单内素材字段提供只读分页数据，**本身不渲染选择器**。 | 正常选素材时不由 Agent 调用；仅收到表单 App 的 `material_pick_request`（宿主不支持 App 内取数）后，在对话中列出候选，等用户文字确认，再将所选素材写回字段 `value`、其余字段按 `draft` 回填，重新调用 `ask_user_interact`。 |
| **需要审批的 API** | Remote MCP 当前没有审批通道；`blue_exec_api` 对 `need_user_approval` API 拒绝执行。 | 如实告知用户无法经 Remote MCP 执行，停止该动作；不得用聊天确认、改 body、CLI 或其他通道绕过审批。 |

> Skill Catalog 的筛选、分类和分页都在同一张 App 卡片内完成；每增加一次 `browse_skills` 调用都会额外生成一张卡片，
> 因此是错误行为。

### `ask_user_interact` 固定调用形态（few-shot，照抄这些结构）

mode 先分清：

- `form`（默认）：要用户填/选/确认。**每轮最多一次；返回后本轮立即结束**——不再输出文字、
  不再调用任何工具，等用户提交的 follow-up。
- `preview`：纯展示（成片、图片等），无确认/取消按钮。**不结束本轮**，可继续输出或调用其他
  工具，无 per-turn 次数限制。

✅ 正确 — 一轮用一个表单收集参数和素材（素材字段要求当前会话已绑定工作区）：

```text
ask_user_interact(mode="form", title="视频参数确认", tabs=[
  {"key": "video", "label": "视频参数", "fields": [
    {"key": "count",  "type": "number", "label": "成片数量", "value": 3, "min": 1, "max": 20, "required": true},
    {"key": "style",  "type": "select", "label": "风格", "required": true,
     "options": [{"label": "电影感", "value": "cinematic"}, {"label": "快节奏", "value": "fast"}]},
    {"key": "bgm", "type": "built_in", "component": "material_picker", "label": "背景音乐",
     "accept": ["audio"], "multi": false, "required": true},
    {"key": "tip",    "type": "info", "content": "提交后开始生成"}
  ]}])
# 工具返回后立刻结束本轮；下一轮从用户消息的 interaction_response.data 读取所选素材
```

✅ 正确 — 展示产物不阻塞（preview），已选素材用 `media_info` 预览：

```text
ask_user_interact(mode="preview", title="成片预览", tabs=[
  {"key": "out", "label": "预览", "fields": [
    {"key": "clip", "type": "media_info", "label": "成片",
     "value": {"url": "https://blueai-video-global.bluemediacdn.com/out.mp4", "name": "成片.mp4", "media_type": "video"}}]}])
# 返回后可继续同轮输出说明文字或调用其他工具
```

❌ 常见错误形态（平台会直接拒绝或产生错误行为）：

| 错误 | 后果 | 正确做法 |
|---|---|---|
| form 调用后继续输出文字或调用其他工具 | 违反「本轮立即结束」 | 调用即停；说明文字放在调用**之前**输出 |
| 一轮里为不同问题调第二次 form | 第一张表单尚未由用户回答，交互顺序混乱 | 第二个表单放到用户提交后的**下一轮** |
| `tabs="[{\"key\":...}]"`（整体序列化成字符串） | 服务端要数组 | 直接传数组对象，禁止字符串化 |
| `select` / `multi_select` 缺 `options` | 校验失败 | `"options":[{"label":"…","value":"…"}]` |
| `info` 字段写 `label` | info 不用 label | `{"key":"tip","type":"info","content":"…（markdown）"}` |
| `range` 用 `min`/`max` 表边界 | 语义错 | 边界用 `min_limit`/`max_limit`，选中值用 `value:{"min":…,"max":…}` |
| `media_info` 的 `value` 传 URL 字符串或本地路径 | 校验失败 | `value` 必须是含心影 CDN HTTPS `url` 的对象，例如 `{"url":…, "name":…, "media_type":"image"}`；其他链接先上传素材库 |
| 默认值写进 `placeholder` | 用户不填时默认值丢失 | 默认值/建议值用 `value`；`placeholder` 只放引导灰字 |
| 使用 `material_preview` / `session_file`，或 `built_in` 的非 `material_picker` 组件 | Remote MCP 只支持 `built_in` 的 `material_picker` | 素材用表单素材字段，预览用 `media_info` 的心影 CDN URL；本地文件先上传后再引用 |
| 为选素材直接调用 `browse_materials`，或收到表单回传后调用提交/查询工具 | `browse_materials` 只取数；Remote MCP 已移除 `submit_interaction` / `get_interaction_status` | 正常通过表单素材字段选；收到 `interaction_response` 后直接继续，取消则停止相应动作 |
| 替用户猜测或提交答案 | 表单是用户决策 | 只预填已确定的默认值；素材选择和变更以用户回传为准 |

字段速查（**Remote MCP 共 10 种**）：`text / textarea / number / range / select / multi_select / checkbox / info / media_info / built_in`。
`built_in` 仅支持 `component: "material_picker"`；`accept` 仅允许 `video / image / audio / ai_video / ai_image / ai_audio`，
可选 `multi`、`material_type`（须在 `accept` 内）和 `query`。返回素材对象含 `material_id / name / url / material_type / cover_url`
（多选为数组）。成片预览用 `media_info`。Remote MCP 表单仅接受 `tabs` 数组，**不接受**本地 MCP 的 `path` 参数；
复杂表单按需精简字段（最多 10 tab、每 tab 16 字段），不要传文件路径。

## 运行流程

完整的 Codex Plugin 主链路见 [references/RUNNER_FLOW.md](references/RUNNER_FLOW.md)。

### 1. 拉取 Skill

```text
browse_skills()  # 每次发现请求只调用一次；App 在本地搜索/分页，不创建 AVP session
-> 等待用户在 App 选择 skill_id
-> get_current_context -> switch_context(mode="skill_runner")  # 仅首次或 Context/mode 变化时绑定 session
-> pull_skill(skill_id)  # 一次返回主 checkout、递归 linked[] 及完整 API grant，并自带 runtime lease
-> sh <plugin_root>/runtime/bin/ideaswork runtime checkout      --workspace <workspace> --skill-name <skill_name> --checkout-id <checkout_id>      --linked-json '<linked[]>' --runtime-endpoint <endpoint> --runtime-lease-stdin
-> 主 Skill 与全部 linked Skills 一次下载校验后，物化到同一个 <workspace>/.avp_run/<主Skill名>/
```

- 正常主路径由 `pull_skill` 在服务端递归展开 linked Skills；直接把响应中的 `linked` 数组传给
  checkout 的 `--linked-json`，不要逐个重复拉取已经下发的子技能。
- `linked=[]` 只表示服务端报告无关联，不证明原 Skill 的必需依赖已满足。若原 Skill 明确要求
  某个子技能但本次未下发，**先尝试补拉**：按已知 id，或将原 Skill 明确给出的名称解析为唯一
  可访问 id，在同一 Context 拉取并物化到主 Skill 的 workspace；成功后继续原流程。
  **补拉仍失败**才停止受影响阶段，报告缺失技能和实际失败原因，不直接认定为部署异常，也不
  擅自改用内置脚本。缺少 `linked` 字段、或 pull 报依赖不完整时，同样先核实并恢复已知依赖；
  具体步骤见 [references/LINKED_RECOVERY.md](references/LINKED_RECOVERY.md)。
- checkout 会先下载并验证主 Skill 与全部 linked archive，再统一物化；linked 的 `skill_dir` 位于主目录
  `linked/<子技能名>/`，`runtime_dir` 位于主 Skill 的 `workspace/.claude/skills/<子技能名>/`，不创建
  独立的 `.avp_run/<子技能名>/`。缺失依赖按上述恢复流程处理；明确无权访问时不绕过权限。
- Codex Plugin 使用随包 Go 二进制提供的 `runtime checkout`，不依赖已安装的全局 CLI，
  也不调用独立 CLI 的 OAuth `skill pull`。checkout 下载由当前 Context 的 Runtime lease endpoint 完成，
  archive 和 bearer 凭证不需要暴露给业务 Python 子进程。
- 主 Skill 的 `CLAUDE.md` / linked prompt 编排由后续 Host 物化步骤处理，不能为了省步骤改写原 Skill。
- standalone CLI 形态可以使用 `ideaswork skill list/pull` 完成同一 Remote MCP control-plane 操作。
- **checkout 的输出是后续所有路径的唯一权威**：`runtime_dir`（技能运行目录）和 `workspace_dir`
  （脚本 cwd / 产物落点）必须使用输出里的值，不要自己猜路径。
- Runtime Core checkout 指下载并物化归档，而非 SHA-256 校验；它仍会检查大小、Zip Slip 和解压上限。
  standalone CLI 的 `pull` 另行校验服务端提供的 hash 和 size。主 Skill 的受管 `CLAUDE.md`
  和 API 清单由后续 Host 步骤处理。
- `pull_skill` 在 Remote MCP 服务端将 checkout 的 `api.json` 绑定为当前 `skill_runner` session 的
  执行 grant；本地 checkout 保留原件，但不复制进 `runtime_dir`。`avp_session_id` 始终保持在
  Remote MCP 服务端，绝不伪造或写入本地文件。

### 2. 按原 Skill 指引执行

读取顺序固定：先 `<workspace_dir>/CLAUDE.md`（受管指引），再主 Skill 的 `SKILL.md`。
sub-skill 只在流程进入对应阶段时加载，禁止预读全部内容。

#### 平台原语固定映射（新 Remote MCP 架构）

Agent-facing 的平台能力只来自 **Remote MCP**；不连接旧 `avp_local` MCP，也不让模型在
Remote / Local tool source 之间猜测。执行前仍要**先发现 MCP 工具**；不同宿主按需展示时，
**未在首屏展示不等于 MCP 不可用**。

| 平台原语 | 固定执行入口 |
|---|---|
| `blue_query_api_docs` | Remote MCP `blue_query_api_docs` |
| `blue_exec_api` | Remote MCP `blue_exec_api` |
| `blue_exec_batch` | Remote MCP `blue_exec_batch` |
| `run_python_script` | `sh <plugin_root>/runtime/bin/ideaswork runtime python --runtime-endpoint <endpoint> --runtime-lease-stdin ...` |
| `sandbox_bash` | Host Bash，在当前 Skill workspace 执行 |
| 平台 Skill 的异步等待 | 统一用 `sh <plugin_root>/runtime/bin/ideaswork runtime wait-result --runtime-endpoint <endpoint> --runtime-lease-stdin ...`。同批多任务必须使用一次 `--tasks-json` 调用。 |
| `ask_user_interact`（含素材字段） | Remote MCP App；需要审批的 API 在 Remote MCP 侧拒绝执行 |

规则：

1. 不改写平台原生 Skill，不把 Python/Bash 源码转换为其它平台原语。
2. `run_python_script` 绝不能裸跑 `python script.py`；必须使用当前 Context 已取得的 runtime lease，经
   `ideaswork runtime python` 运行，使 `call_platform_api` / `call_plat_api` 被注入，且 OAuth / Engine execution token 不进入 Runtime 或 Python 子进程。
3. `sandbox_bash` 直接使用 Host Bash；它不是平台 sandbox，必须明确本地文件系统风险。
4. 所有异步任务统一由本地 Runtime Core `ideaswork runtime wait-result` 等待并获取最终查询结果，
   返回 succeeded / failed / timeout JSON。多个任务必须合并到一次 `--tasks-json` 调用，
   使用 `--completion-policy all|any|cnt:N` 汇总。
5. **禁止用 shell `sleep`、多个并发 `wait_result` 或反复 `--max-polls 1` 充当轮询器。**首次延迟使用
   `wait_result --initial-delay <秒>`；长任务让同一个 `wait_result` 进程完成整段等待。宿主暂时返回
   process/session id 时，只续接该进程，不新建第二组轮询。
6. `ask_user_interact` 返回 MCP App 后结束本轮；用户确认/取消以普通用户消息中的 `interaction_response` 回传，核对 `interaction_id`、`action` 和 `data` 后直接继续。表单不持久化服务端状态，无提交/状态工具往返；不能预设用户选择。
7. Remote MCP 没有审批 App 或提交工具。`blue_exec_api` 拒绝 `need_user_approval` API 时停止并说明限制；不能把聊天确认当作审批，也不能通过其它通道绕过。
8. Remote MCP 不可用时停止并说明远端能力不可用；CLI 是 Remote MCP 的终端客户端，不能静默绕过 Remote MCP 直连 Engine 或回退旧 `avp_local` / `local_rpc`。
9. Runtime Core 输出 `status="lease_recovery_required"`，或包含 `error_code` 为 `runtime_lease_*` 时，
   这是**给 Agent 的控制信号**，不是 Skill 的业务结果：
   - `next_action="create_runtime_lease"`：当前 Context 未变时，调用该 MCP tool 获取新 lease，立刻把本轮后续 Runtime Core 命令全部切到新 lease；只重跑**尚未完成的单个命令**，不得让其他并发命令继续拿旧 lease；
   - `next_action="get_current_context_then_create_runtime_lease"`：先读取并确认当前 Context。若团队或项目已被切换，不能自动重跑之前的写操作；
   - `next_action="retry_runtime_call"`（例如 `runtime_lease_busy`）：**原 lease 仍有效，不调用 `create_runtime_lease`**。Runtime Core 对明确的 busy 拒绝已做短暂的有限重试；仍冲突时避免并发使用同一 lease，稍后重试尚未完成的调用。可能有部分副作用的 Python 脚本须先核对 Skill 状态，不盲目重跑；
   - checkout 和纯查询型 wait-result 可用新 lease 重试；Python 脚本可能已经产生部分副作用，必须先根据 Skill 状态判断，必要时向用户确认，不能盲目重跑。

Runtime Core 由 Plugin 与独立 CLI 复用实现：Plugin 使用 `pull_skill` 返回（或 `create_runtime_lease` 重签）的 lease 驱动 Runtime Core；独立 CLI 可采用自己的 OAuth transport。Plugin 随包携带 CLI，但不读取 CLI OAuth session。

### Skill 发现必须优先使用 MCP App

用户问“有什么 Skill”、想找/搜索/浏览/比较 Skill、询问类似 Skill，或按关键词、分类、来源获取
Skill 推荐时，**必须先调用 `browse_skills`**，让 Skill Catalog MCP App 展示可搜索、分页的交互列表。
不要直接在对话中手工罗列 Skill，也不要把 `ideaswork skill list` 作为首选路径。宿主不能渲染 MCP
Apps 时仍先调用 `browse_skills`，使用它返回的文本 fallback；只有 MCP 工具不可用，或用户明确要求
CLI 输出时，才允许降级到 CLI。

### 3. 处理异步结果

所有异步任务统一使用本地 Runtime Core `sh <plugin_root>/runtime/bin/ideaswork runtime wait-result`，在当前轮次等待并获取最终结果。
即使平台 Skill 写的是事件等待或旧异步注册原语，也映射到本地等待器。Remote MCP 返回
`wait_result_hint` 时使用其中的查询 API 和完成条件，并从实际创建响应中提取任务查询参数；
未提供完整信息时先查询 API 文档和 Skill，不能把提交成功、事件订阅或唤醒提示当作最终结果。
若没有可用查询 API，停止并说明无法在当前宿主取得异步结果。

- 单任务使用 `--query-api-code`、`--params-json`、`--completion-json`。
- 同一批多任务使用**一次** `--tasks-json`，每项包含 `key / query_api_code / query_params /
  completion_config`，并用 `--completion-policy all|any|cnt:N` 汇总；Runtime Core 会在每轮内串行查询，
  已终态任务不再查询，同一 lease 不会被多个进程并发占用。
- 首次查询需要延迟时使用 `--initial-delay <秒>`；禁止另外启动 shell `sleep`。
- 一次调用应覆盖合理的完整等待窗口。只有返回 `timeout` 且任务仍需继续时，才用同样参数开始下一段；
  不要通过连续 `--max-polls 1` 手工轮询。

示例：

```bash
sh <plugin_root>/runtime/bin/ideaswork runtime wait-result \
  --tasks-json '[{"key":"scene_1","query_api_code":"task_status","query_params":{"task_id":1},"completion_config":{"field":"data.status","op":"eq","value":"SUCCESS"}},{"key":"scene_2","query_api_code":"task_status","query_params":{"task_id":2},"completion_config":{"field":"data.status","op":"eq","value":"SUCCESS"}}]' \
  --completion-policy all --initial-delay 30 --interval 15 --max-polls 20 \
  --runtime-endpoint <endpoint> --runtime-lease-stdin
```

不要把等待委派给子 agent。恢复后只依据查询结果和已持久化文件继续，不依赖异步前的临时上下文。

### 4. 汇报结果

**回复只讲用户要的结果。执行层的问题尽量不披露，只有阻断性问题才说。**

必说：**业务产物**——成片/文件/链接，以及用户用得上的关键属性（时长、比例、素材 ID、本地文件位置）。

只有下列**阻断性**情形才披露问题；用一两句用户听得懂的话说，并带上需要用户做的决定或下一步：

- 目标没达成：核心产物缺失或不完整、质检/门禁没通过、只做完了一部分。
- 需要用户行动：缺必填输入、需要确认或授权、权限或额度不足、需审批的 API 被拒绝。
- 结果不能按字面使用：用了占位/示意的输入（例如用 AI 生成的示意图代替真实商品图），或与要求有实质偏差。
- 多花了钱或可能重复计费：重复提交、重试产生额外费用、无法确认某次提交是否生效。
- 涉及隐私或授权边界（如人像）。

**默认不披露**，一律不写进回复，哪怕你知道：

- Skill 脚本或契约的缺陷、响应格式对不上、你已绕过去的内部报错；
- 本地与平台的差异点及其编号（F1–F13），以及不影响本次产物的“未完整验证”环节；
- 降级或兜底路径（改用 CLI、从列表找回任务 ID 等）、逐步的任务 ID 链路、重试细节；
- “建议回 Builder 修脚本”“把缺口沉淀成修复”这类建议。

能绕过就静默绕过并把任务做完；绕不过、真的影响结果了，它就属于上面的阻断性情形，按那一条说。
**不披露不等于隐瞒**：凡影响结果真伪、可用性、费用或用户要做的决定的事实都必须说，也不能把失败说成成功。

下一步建议只给业务向的一两个选项（如换素材重跑、换创意方向），不列执行层的选项。

✅ 用户视角（把内部限制翻译成对用户有影响的一句事实，其余不提）：

```text
成片已生成：5 秒 · 9:16 · 1080p，带环境音。
- 在线播放：<url>
- 本地文件：<path>
成片在项目素材库里（material_id 176511），没有归入成片库文件夹。
⚠️ 商品图是按你的要求用 AI 生成的示意图，成片里的商品外观只对应这张图；用于真实投放请换成真实商品图重跑。
要换真实商品图重跑，还是换一个创意方向？
```

❌ 不要这样：分“业务产物 / 未能完整验证 / Skill 自身问题 / 降级清单”四大块，列出 F 编号、脚本解析缺陷、
各步骤任务 ID、兜底路径，再建议用户去 Builder 修脚本。用户不需要，也无法据此做任何决定。

用户**明确要求**修改或重新设计该 Skill 时，才切换到 `ideaswork-builder`，不要在拉取副本上静默修补；
不要主动劝用户去 Builder。

## 边界

- Runner 不包含 Builder、模板、差异提报或发布逻辑。
- Runner 不实现平台原语；平台能力仍由 Remote MCP/lease endpoint 提供，本地 CLI 与 Runtime Core
  控制面编入 `ideaswork-cli` 发行包的同一个 Go 二进制，不依赖旧 `avp_local` Python 包。
- 顶层宿主 Adapter 暂不打包；本地 `wait_result` 是 Runtime Core 的 portable 等待，不是回调。
- 同一问题失败三次后停止重试，保留证据并向用户说明阻塞点。

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
