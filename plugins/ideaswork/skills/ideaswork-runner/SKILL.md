---
name: ideaswork-runner
description: IdeasWork（心影）线上已发布 Skill 的**首要发现与运行入口**。用户通过 IdeasWork 询问「有什么/有哪些/可用哪些/找一下/搜索/推荐 skill」「心影有哪些 skill」「帮我找个 skill」时，默认指**远端已发布 Skill Catalog**，必须先查询远端 Catalog：走 `browse_skills`，不能把当前工作区、Codex 已安装 Skill、插件 Runner/Builder 说明或本地文件误当答案。仅当用户明确说「本地/已安装/Codex/工作区 skill」时才讨论本地 Skill。也用于拉取、运行或验证已发布心影 Skill；设计、转化、打样、发布 Skill 属于 ideaswork-builder。
---

# IdeasWork Runner

## 执行入口（Plugin：只有 Remote MCP）

本制品只有一条执行链路：宿主已连接的 IdeasWork Remote MCP。平台能力、Catalog、Context、表单都走 MCP 工具；
本地只做三件事——**用 curl 下载并解压 checkout、用随包 `scripts/bridge.py` 跑 Python 脚本、用 curl 上传文件**。
没有 `ideaswork` 命令、没有 npm 安装、没有独立 CLI；不要寻找或安装它们。连接缺失时按下面「OAuth 登录门」恢复，
不换身份、不用裸 HTTP 冒充 MCP。

把一个**已发布**的线上 Skill 拉到本地，优先按它自己的指引和 `api.json` 跑完。
不在 immutable checkout 上直接修改业务指引。用户明确要修改、转化或把执行成果沉淀成新 Skill 时，
衔接 `ideaswork-builder` 并使用独立草稿；直接使用/组合能力时可衔接 `ideaswork-capability`。
三个指引不是账号角色，不要求换包或重新登录；交接保留已确认的工作区、素材、参数、任务 ID 与真实结果。
连续调用多个 API 不自动进入 Builder。

## 运行环境要求

本制品的本地步骤只依赖 `curl`、`python3`（3.10+，`bridge.py` 的子进程需要；解压和校验用标准库即可）和一个 POSIX shell
（macOS / Linux / WSL）。**原生 Windows 不在本制品的本地步骤支持范围内**：需要下载 checkout、跑 Python 或上传文件时，
如实告诉用户该环境暂不支持，请其在 macOS / Linux / WSL 下继续；不要改写成 PowerShell 变通写法。纯 MCP 能力
（Catalog、Context、`blue_*` API、表单）不受影响。

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

- **主 Skill**：你 `pull_skill` 的那个技能；运行目录固定为 `<cwd>/.avp_run/<主Skill名>/workspace/`。
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
   `List MCP resources` 代替 Catalog 查询。

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

## 前置条件（按顺序执行）

### 0. 首次使用的 OAuth 登录门

先检查当前 task 是否已经注入任意一个 IdeasWork Remote MCP tool（例如 `browse_skills`、
`get_current_context` 或 `browse_contexts`）。

- **已经注入**：直接继续下一步。
- **一个都没有**：这是 Codex Plugin 的连接/授权状态，不是让 Agent 在终端代替用户登录的信号。提示用户在
  插件页完成或重新触发 **Connect IdeasWork**；安装策略为 `authentication: "ON_INSTALL"`，Codex 应在安装时
  通过该插件声明的 OAuth-protected Remote MCP 请求用户授权。用户完成浏览器中的登录和授权后，新建或重连
  IdeasWork task，使 Remote MCP tools 与 MCP Apps 注入。

  已安装但仍无工具时，先让用户检查插件连接状态或重新连接；不要执行 `codex mcp login`，
  也不要用裸 HTTP `/mcp`、本地 token 或 `List MCP resources` 冒充 Codex MCP connection。

> Plugin manifest 只关联 `.mcp.json` 的 Remote MCP；OAuth UI 和 token 由 Codex host 与 MCP 的 protected-resource
> discovery 负责。本地的 curl 与 `bridge.py` 不能、也不应读取该 token，它们只使用 runtime lease。

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
     `browse_contexts` 获取最新候选（见上文「工作区边界」，先问用户，不静默切换），再用本次团队/项目名称构造 `ask_user_interact` 的 `select`，
     结束本轮等待提交。只把用户所选项对应的本次 `context_ref` 传给 `switch_context`，不用旧卡片或缓存 ref，
     不替用户猜选其他工作区。其他认证/权限失败按实际错误处理，不把选工作区当作通用修复。
   - 只有用户明确要求新会话才设置 `new_session=true`。若明确报告原 Context 丢失，先恢复原工作区，
     不静默落回 OAuth 默认项目、不重放业务调用。
   `switch_context` 才会绑定 team、project 与隐藏的 AVP session；不要传入或伪造 `avp_session_id`。
   `pull_skill` 返回 immutable checkout 的元数据（`checkout_id`、`sha256`、`size_bytes`、`linked[]`），归档本身由你按下文
   「物化 checkout」用 curl 下载、校验并解压到当前 workspace。
3. `pull_skill` 的返回**自带当前 skill_runner Context 的 runtime lease**（`runtime_endpoint` 与
   `runtime_lease`，随 pull 输出中的 `runtime_lease` 字段下发），下载 checkout、Python 脚本、上传文件都复用它。
   **lease 的使用规则（不可违反）**：只经 **stdin** 传给 curl（`-H @-`）或 `bridge.py`（`--runtime-lease-stdin`）；
   不写进命令行参数、环境变量、Skill 文件、日志或传给 Python 子进程。仅在 lease 失效、额度耗尽或 Context 改变后，
   才调用 `create_runtime_lease` 重签（有效 Context 的重复请求返回同一 lease，**不会延长它的到期时间**）。
   **有效期由服务端下发，不在文档或脚本里写死**；以返回的 `expires_in` / `remaining_calls` 判断剩余预算，
   不为延长有效期提前重签。**同一 lease 的调用必须串行**：不要并发下载、并发跑脚本或并发上传。
   每次 checkout 下载、每次上传、每次脚本内的平台 API 调用都消耗额度。
4. 读 [references/EXECUTION_PARITY.md](references/EXECUTION_PARITY.md) 的「能力映射」和
   「已知失真点」两节。本地与平台的全部语义差在那份文件里，本文不重复。

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
| **Skill Catalog**：`browse_skills()` | 浏览当前账号可见的已发布远端 Skill；按**Skill 分类**、名称、来源、状态、描述筛选；本地翻页；选择一个 Skill。分类 chip 是发现 Skill 的首选入口，卡片上的 `category` 是该 Skill 的权威分类。 | 用户问“有什么 Skill”“有哪些分类”“按类别找/推荐 Skill”时，**只调用一次且不传参数**，然后结束本轮等待用户在 Catalog 中按分类或搜索选择。不要手写一份分类/Skill 清单，不要调用 `get_skill_catalog_records`，不要为翻页或换分类再次调用 `browse_skills`。目录的「我的 Skill」列出用户自己的全部 Skill（含草稿、已禁用）；点「管理」会以含 `skill_manage_requested` 的用户消息回到对话，此时不拉取运行，改用 `list_skill_versions` / `manage_skill_version` / `update_skill` 继续，影响他人的变更（设为当前版本、启用、`derivable`、子技能）先让用户明确确认，详见 ideaswork-builder 的「提交之后：属主管理」。 |
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
-> 对主 Skill 和 linked[] 的每一项：下载 → 校验 → 解压（见下「物化 checkout」）
```

#### 物化 checkout（逐项执行，主 Skill 与 `linked[]` 每项相同）

`pull_skill` 的每个 checkout 对象含 `checkout_id`、`skill_name`、`sha256`、`size_bytes`。
`<endpoint>` 是 `runtime_endpoint` 把末尾的 `/call` 换成 `/checkouts/<checkout_id>`。
工作区目录固定为 `<cwd>/.avp_run/<主Skill名>/workspace/`（后文记作 `<workspace>`），脚本 cwd 与产物都在这里。

1. **下载**（lease 经 heredoc 走 stdin，不出现在命令行，已验证 `ps` 中不可见）：

   ```sh
   mkdir -p ".avp_run/<主Skill名>/_dl"
   curl -fsS --max-filesize 52428800 -H @- -o ".avp_run/<主Skill名>/_dl/<skill_name>.zip" \
     "<endpoint 把 /call 换成 /checkouts/<checkout_id>>" <<'EOF'
   Authorization: Bearer <runtime_lease>
   EOF
   ```

   `--max-filesize 52428800` 是 50 MiB 上限。不跟随重定向（不要加 `-L`）：lease 不能被转发到别的主机。
   非 200 时 curl 返回非零；响应体是结构化错误，按下文「lease 失效」处理，不重试创建类操作。
2. **校验**（任何一项不符就删除该 zip、**不解压**、不重试，报告 `checkout 校验失败`）：
   - 字节数等于 `size_bytes`；
   - SHA-256 等于 `sha256`：`python3 - <<'PY'` 里 `hashlib.sha256(open(path,'rb').read()).hexdigest()`，
     或 `sha256sum` / `shasum -a 256`（以系统可用者为准，不要自己心算）。
3. **解压**——只用 Python 标准库，**不要用 `unzip`**（各平台对 `..` 路径的处理不一致）：

   ```sh
   python3 -m zipfile -e ".avp_run/<主Skill名>/_dl/<skill_name>.zip" ".avp_run/<主Skill名>/workspace/.claude/skills/<skill_name>"
   ```

   已验证：`python3 -m zipfile -e` 会把 `../x`、`/abs/x` 这类成员收进目标目录内而不是逃逸，软链成员只会落成普通文件。
   解压后立即做两项检查，失败就删除整个 `.claude/skills/<skill_name>/` 并报告：
   - 目录里必须有 `SKILL.md`；
   - 文件总数不超过 2000、总大小不超过 200 MiB（`find` / `du` 即可）。
4. **删除不该保留的文件**：解压出的 `api.json` 与 `__skill_meta.json` 不留在运行目录里
   （`api.json` 由服务端在 pull 时绑定为 grant，本地不依据它扩权）。
5. **linked 子技能**：对 `linked[]` 每一项重复 1–4，**写入同一个 `<workspace>/.claude/skills/<子技能名>/`**，
   不创建子技能自己的 `.avp_run` 目录；`linked` 最多 32 项，名称不得重复，也不得与主 Skill 同名。
6. 全部成功后再删除 `_dl/`。任何一项失败：删掉本次已解压的目录，不留半成品，向用户说明是哪个 Skill、哪一步。

- 正常主路径由 `pull_skill` 在服务端递归展开 linked Skills；直接消费响应中的 `linked` 数组，不要逐个重复拉取。
- `linked=[]` 只表示服务端报告无关联，不证明原 Skill 的必需依赖已满足。若原 Skill 明确要求
  某个子技能但本次未下发，**先尝试补拉**：按已知 id，或将原 Skill 明确给出的名称解析为唯一
  可访问 id，在同一 Context 拉取并物化到主 Skill 的 workspace；成功后继续原流程。
  **补拉仍失败**才停止受影响阶段，报告缺失技能和实际失败原因，不直接认定为部署异常，也不
  擅自改用内置脚本。具体步骤见 [references/LINKED_RECOVERY.md](references/LINKED_RECOVERY.md)。
- **没有受管 `CLAUDE.md`**：服务端已退役 `claude_prompt`，`pull_skill` 不返回它，checkout 也不会生成该文件。
  技能指引就在主 `SKILL.md` 里，不要为了"补全"去创建或改写 `CLAUDE.md`。
- **路径以你创建的为准**：`<workspace>`（脚本 cwd / 产物落点）和 `<workspace>/.claude/skills/<名>/`（技能运行目录）
  就是上面固定的位置，不要自己猜别的路径。
- `pull_skill` 在服务端将 checkout 的 `api.json` 绑定为当前 `skill_runner` session 的执行 grant；
  `avp_session_id` 始终保持在 Remote MCP 服务端，绝不伪造或写入本地文件。

### 2. 按原 Skill 指引执行

先读主 Skill 的 `<workspace>/.claude/skills/<主Skill名>/SKILL.md`。
sub-skill 只在流程进入对应阶段时加载，禁止预读全部内容。

#### 平台原语固定映射（Plugin：Remote MCP + curl + bridge.py）

Agent-facing 的平台能力只来自 **Remote MCP**；不连接旧 `avp_local` MCP，也不让模型在
Remote / Local tool source 之间猜测。执行前仍要**先发现 MCP 工具**；不同宿主按需展示时，
**未在首屏展示不等于 MCP 不可用**。

| 平台原语 | 固定执行入口 |
|---|---|
| `blue_query_api_docs` | Remote MCP `blue_query_api_docs` |
| `blue_exec_api` | Remote MCP `blue_exec_api` |
| 批量执行 | Remote MCP `blue_exec_api`，传 `calls` 而不是 `api_code` / `body` |
| `run_python_script` | `python3 <runner_skill_dir>/scripts/bridge.py ...`（见下「运行 Python 脚本」） |
| `sandbox_bash` | Host Bash，在当前 Skill workspace 执行 |
| 平台 Skill 的异步等待 | Remote MCP `blue_exec_api` 反复调用状态查询 API（见下「3. 处理异步结果」） |
| 本地文件进素材库 | `curl` 上传到 `material_upload_endpoint`（见文末「本地素材上传」） |
| `ask_user_interact`（含素材字段） | Remote MCP App；需要审批的 API 在 Remote MCP 侧拒绝执行 |

`<runner_skill_dir>` 是本 `SKILL.md` 所在目录。

##### 运行 Python 脚本

`run_python_script` 绝不能裸跑 `python script.py`：裸跑没有注入 `call_platform_api`。必须经随包的 `bridge.py`：

```sh
python3 <runner_skill_dir>/scripts/bridge.py \
  --runtime-endpoint "<runtime_endpoint>" --runtime-lease-stdin \
  --workspace "<cwd>/.avp_run/<主Skill名>/workspace" \
  --script ".claude/skills/<skill_name>/tools/x.py" \
  --args-json '["--flag","value"]' <<'EOF'
<runtime_lease>
EOF
```

- `--script` 与 `--python-path-json` 的相对路径都以 `--workspace` 为基准；脚本必须在 workspace 内。
- 输出是一个 JSON：`success / exit_code / stdout / stderr`，超时多一个 `timeout:true`（默认 `--timeout 3600` 秒，
  可调）。退出码：0 成功，1 脚本失败，**6 平台调用结果未知（不要重放）**，7 lease 需要处理，2 参数或解释器问题。
- 子进程需要 Python 3.10+。`python_version_unsupported` 时请用户安装 3.10+，用 `--python-executable <路径>` 指定，
  并同样用该解释器启动 `bridge.py`；脚本没有执行。
- 脚本里直接调用 `call_platform_api(api_code, body)`（也注入 `call_plat_api`、`blue_exec_api` 等旧名字和 `avp_local`
  模块），写法与平台一致，**脚本一行不改**。`__call_platform_api_file:<workspace相对路径>` 的上传由 bridge 父进程完成。
- `bridge.py` 是凭据隔离层：父进程只从 stdin 读 lease；子进程拿不到 lease，也看不到名字含 TOKEN / LEASE / SECRET
  的环境变量。它不是文件系统沙箱，脚本仍能读写本机文件，所以要像对待任何本地脚本一样对待来源不明的 Skill。

规则：

1. 不改写平台原生 Skill，不把 Python/Bash 源码转换为其它平台原语。
2. `sandbox_bash` 直接使用 Host Bash；它不是平台 sandbox，必须明确本地文件系统风险。
3. `ask_user_interact` 返回 MCP App 后结束本轮；用户确认/取消以普通用户消息中的 `interaction_response` 回传，核对 `interaction_id`、`action` 和 `data` 后直接继续。表单不持久化服务端状态，无提交/状态工具往返；不能预设用户选择。
4. Remote MCP 没有审批 App 或提交工具。`blue_exec_api` 拒绝 `need_user_approval` API 时停止并说明限制；不能把聊天确认当作审批，也不能通过其它通道绕过。
5. Remote MCP 不可用时停止并说明远端能力不可用；不能静默绕过 Remote MCP 直连 Engine 或回退旧 `avp_local` / `local_rpc`。
6. **lease 失败信号**：`bridge.py` 输出的 `error_code` 以 `runtime_lease_` 开头（退出码 7），或 curl 响应体里
   `error.code` 以 `runtime_lease_` 开头，是**给 Agent 的控制信号**，不是 Skill 的业务结果。按 `next_action`：
   - `create_runtime_lease`：当前 Context 未变时调用该 MCP tool 重签，之后所有本地命令改用新 lease；只重跑**尚未完成的单个命令**；
   - `get_current_context_then_create_runtime_lease`：先读取并确认当前 Context。若团队或项目已被切换，不能自动重跑之前的写操作；
   - `retry_runtime_call`（如 `runtime_lease_busy`）：**原 lease 仍有效，不要重签**。`bridge.py` 对明确的 busy 拒绝已做有限重试；仍冲突就稍后重试，并避免并发使用同一 lease；
   - checkout 下载可用新 lease 重试；Python 脚本可能已有副作用，必须先核对 Skill 状态，必要时问用户，不能盲目重跑。
7. **结果未知不重放**：`runtime_request_outcome_unknown`（退出码 6）、`push_result_unknown`、上传超时，都表示请求可能已经执行，
   先核实远端状态（素材库、版本历史、任务列表）再决定，不自动重试。

### Skill 发现必须优先使用 MCP App

用户问“有什么 Skill”、想找/搜索/浏览/比较 Skill、询问类似 Skill，或按关键词、分类、来源获取
Skill 推荐时，**必须先调用 `browse_skills`**，让 Skill Catalog MCP App 展示可搜索、分页的交互列表。
不要直接在对话中手工罗列 Skill。宿主不能渲染 MCP Apps 时仍先调用 `browse_skills`，使用它返回的文本 fallback；
MCP 工具不可用时停止并说明远端能力不可用，不改用其他入口。

### 3. 处理异步结果

本制品没有本地等待器。异步任务用 **Remote MCP `blue_exec_api` 反复调用状态查询 API** 取得最终结果；这条路径走宿主 OAuth，
**不用 lease，也不占 lease 额度**。即使平台 Skill 写的是事件等待或旧异步注册原语，也按本节执行。

**提交成功不等于完成**：不要把任务创建成功、事件订阅或唤醒提示当作最终结果。

1. 取查询方式：优先用创建响应里的 `wait_result_hint`——`query_api_code`（状态查询 API）、`completion_config`（完成条件）。
   查询参数从**创建响应里的真实任务 ID**组织。该查询 API 的文档若本 Context 还没查过，先 `blue_query_api_docs`。
2. `wait_result_hint` 带 `task_id` 与 `fallback` 时（创建响应里能取到平台基础任务 ID），主查询查不到就直接用
   `fallback.query_api_code` 和 `fallback.params`，同样先查它的文档。
3. 提醒：任何异步任务，若按 Skill 原语或 `wait_result_hint` 指向的查询 API 查不到结果，可改用 `task_status` 尝试，
   `task_id` 取创建响应里的真实任务 ID，完成条件看 `data.status`（可加 `fail_if` 判失败）。典型如
   `t2v_session_task_create`：会话里没有 generation 行，响应无 `avp_event_id`，hint 里的 `t2v_session_task_query`
   按会话查恒为空，应改用 `task_status`，`task_id` 取 `data.data.base_task_id`。`task_status` 不返回 `cdn_url`，
   需要时再查 `task_detail`；若报缺少 `project_id`，补当前 Context 的项目 ID。仍查不到就停止并说明无法取得异步结果。
4. **判定规则**（按 `completion_config` 逐字执行，不凭感觉）：`field` 是用 `.` 分隔的路径（不含 `[]`）；`op` 默认 `eq`，
   支持 `eq / ne / in / not_in / contains / exists / gt / gte / lt / lte`；`all_of` / `any_of` 是规则数组；
   `fail_if` 命中即判**失败**（优先于成功判定）。字段不存在时不是失败，视为"还没完成"，除非规则用了 `exists`。
   不能拿传输层的 `code` / `status` / `message` 当完成字段。
5. **轮询方式**：同一批互相独立的任务，在**一次** `blue_exec_api(calls=[…])` 里合并查询，已到终态的任务不再查。
   两次查询之间用 Host Bash `sleep <秒>` 间隔（首次可先 `sleep 30`，之后约 15 秒），这里没有 lease，不存在并发占用问题。
   一段等待窗口的总次数要有上限（例如 20 次），到上限仍未终态就**如实汇报"仍在生成"和任务 ID**，由用户决定是否继续；
   **不要重新提交创建请求**，创建过的任务只查询、不重建。
6. 多任务汇总策略自己按需求判定：全部成功才算成功（默认）、任一成功即可、或达到 N 个成功；有 `fail_if` 命中的任务单独报告。

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
- Runner 不实现平台原语；平台能力由 Remote MCP 提供。本地只有 curl、Python 标准库解压和 `scripts/bridge.py` 三样东西，
  不依赖 Go、npm、独立 CLI 或旧 `avp_local` 包。
- 顶层宿主 Adapter 暂不打包；轮询等待不是回调，不会自动唤醒宿主。
- 同一问题失败三次后停止重试，保留证据并向用户说明阻塞点。

## 本地素材上传

- 用户指定本地文件、或 Skill 需要将本地产物入素材库时，复用 `material_upload_proxy`。
  先确认当前 Context 和 API 文档/grant（先 `blue_query_api_docs("material_upload_proxy")`），
  不能把本机文件路径直接发给 `blue_exec_api`。
- 在 Python 脚本里：沿用 `call_platform_api("material_upload_proxy", {"file": "__call_platform_api_file:<workspace相对路径>", ...})`，
  由 `bridge.py` 父进程上传，子进程不接收 lease；返回 `material_id`，不再补一次上传 API。
- 脚本之外直接上传一个文件，用 curl 发到 pull / `create_runtime_lease` 载荷里的 `material_upload_endpoint`：

  ```sh
  curl -fsS -X POST -H @- --max-time 900 \
    -F 'body={"<API 文档要求的其它参数>":"..."}' \
    -F 'file=@<本机文件路径>' \
    "<material_upload_endpoint>" <<'EOF'
  Authorization: Bearer <runtime_lease>
  EOF
  ```

  `body` 是不含 `file` 的 JSON 对象（至多 64 KiB），`file` 恰好一个、非空、至多 500 MiB。两个字段都必须有，且不要再加别的字段。
  上传前先确认路径在当前 workspace 内、是普通文件（不是软链）。
- lease 缺失/过期：通过当前 MCP 获取新的 lease；Context 改变先确认 Context。
- **超时或结果未知不自动重传**：Engine 的 MD5 复用不保证素材创建幂等，重传可能重复创建素材。先检查素材库再决定。
