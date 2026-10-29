---
name: ideaswork-builder
description: 用户明确要求把已完成的 IdeasWork 能力组合或运行成果沉淀成可复用 Skill，或明确要求从需求、SOP、已有 Skill 开始构建/转化时使用。承接真实执行证据，完成参数化、验证和本地交付；用户没有要求提交/推送时不提交也不提示。日常生成、处理或多 API 组合使用 Capability；运行已发布 Skill 使用 Runner，不因多次调用自动进入 Builder。
---

# IdeasWork Builder

> 本制品不内置原生程序：首次需要本地 Runtime Core 命令前，先读 [references/PLUGIN_RUNTIME.md](references/PLUGIN_RUNTIME.md) 检查并按指引安装；Windows 原生环境用其中的 `.cmd` 写法，不要用 `sh`。

## 执行入口选择（先于后续工具指引）

- 制品明确为 `cli`、用户明确使用独立 CLI，或当前是仅提供 Shell/文件读写且没有原生 IdeasWork MCP 的
  Harness：先读 [references/CLI_BINDING.md](references/CLI_BINDING.md)，使用 CLI 绑定。
  该绑定替代后文 Remote MCP/App/lease 的调用方式，但不改变业务 Skill、用户授权或服务端权限边界。
- 已配置 Remote MCP 的制品/任务：沿用下文 Remote MCP 主链路。连接缺失时按插件连接指引恢复，
  不因工具暂未注入自动切换 CLI 身份，不把 CLI 当作权限或审批失败的绕过通道。


只在用户明确要求构建、转化或沉淀 Skill 时进入；本地创作不要求 Builder 角色或 `skill.write`。
日常完成任务用 `ideaswork-capability`，运行线上 Skill 用 `ideaswork-runner`。三个指引可以连续衔接，
无需换包或换账号；切换指引不扩大远端授权。

## 两个构建入口（先判断，再选择模式）

- **从已完成的工作沉淀（常见路径）**：用户先用 Capability 组合能力或运行 Skill，之后明确要求“把刚才这套做成 Skill”。
  先读 [references/WORKFLOW_CAPTURE.md](references/WORKFLOW_CAPTURE.md)，承接已确认需求、素材、调用和成功证据，
  不重问已知信息、不默认重跑生成。多次 API 调用本身不是 Builder 触发条件。
- **直接构建（专业路径）**：用户明确提出构建目标或提供具体 Skill，沿用下方转化/打样阶段。
  需要发现/验证能力时复用现有平台入口，不要求用户反复切换角色。

这两个入口不新增 CLI 模式或服务端 mode。完成入口判断后，仍按已有两种构建模式和阶段推进。

## 先选择模式

| 模式 | 适用输入 | 目标与产出 | 阶段 |
|---|---|---|---|
| 转化模式（`conversion`） | 已有一个相对完整、可识别的具体 Skill：Skill 定义、Prompt、工具调用流程或能独立表达该能力的一组脚本/配置 | 迁移、适配并标准化为可用的平台 Skill | `01 → 02 → 03 → 04 → 05 → 06` |
| 打样模式（`sampling`） | 没有现成 Skill，输入是明确的业务流程、业务需求、能力想法、人工 SOP 或待自动化任务 | 从 0 整理、构建并验证一个实际可用的平台 Skill | `01 → 02 → 03 → 04 → 05 → 06` |

模式只按输入是否已有**具体 Skill**判断：已有具体 Skill → 转化；没有现成 Skill、需要从业务流程/想法/需求构建 → 打样。
已有执行成果通常作为打样的验证证据；只有整体已构成可识别的具体 Skill 时才用转化。不要因为有调用历史就自动判为转化。
沉淀入口仍逐阶段读取指引，但已确认需求和可复用证据直接承接；阶段完成不等于把已完成工作重新做一遍。

打样不是概念验证、假设方案或只探索 API。API 发现和低成本真实调用只是构建中的验证步骤；最终仍要产出通过静态校验、能承载核心业务流程的 Skill。若用户只要求孤立地查询某个 API 而不构建 Skill，不要把该活动误称为打样模式。

## 全局规则

1. 每进入一个阶段时才读取对应 `sub_skill_XX/SKILL.md`，禁止预读全部阶段。
2. 先完成 `sub_skill_01_preflight` 的模式与上下文检查；复用已确认信息。纯本地编写/校验不以远端登录、Builder Context 或写入权限为前提，远端动作再检查连接及授权。
3. 先查 API 文档，再执行 API；昂贵、批量、发布、删除等操作必须先取得用户确认。
4. 薄脚本只保留机械转换，业务编排写在 Skill 指令中。平台脚本中的 `call_platform_api(api_code, body)` 迁移前后保持不变。
5. `api.json` 统一为 dict：键为真实查询文档并验证过的 `api_code`，值为一句话用途说明；`__` 前缀键为注释/分组说明，不计入白名单。它是 DB `api_codes` 的唯一文件来源，不另建清单；未知能力先作为待确认或阻塞证据，不臆造 API。
6. 不显示 token，不把身份配置、草稿缓存或本地产物提交入库。
7. 同一问题失败三次后停止重试，保留证据并说明阻塞点。
8. 默认不切换工作区：只在用户明确要求、或当前工作区确实无法继续时才换，换之前把“从 A → 到 B”告诉用户并得到同意，
   不静默切换、不因缺 Skill/API/权限而自行换项目。CLI 的 `context use <ref>` / `team use` / `project use` 对不同工作区需要
   用户同意后才加的 `--confirm-switch`，Agent 不得自行添加。

### 问题分类与反馈原则

问题提报服务于 Skill 落地，不是 Builder 的目标。先保障核心业务目标，再按以下顺序判断：

1. **Skill 自身问题**：Prompt、指令、编排、参数映射、状态落盘或验证不足。先修复 Skill；不因其提平台或 Agent 问题。
2. **平台 Tool 能力问题**：平台提供的 Tool、Model、API、参数或 API 行为确实缺失/错误，且没有合理绕过方案。标为平台能力问题，反馈入口为 <https://bluefocus.feishu.cn/share/base/form/shrcnB3SRCUsabcsTcyiS0V4O8g>。
3. **Agent Runtime / Agent Framework 能力问题**：Skill 设计合理，但 Runtime/Framework 缺少或错误实现执行能力，例如 Sub Agent、上下文传递、Tool 回调、异步恢复或运行时执行逻辑。不要归为平台 Tool 缺失；反馈入口为 <https://bluefocus.feishu.cn/share/base/form/shrcnpGPjWDbCjPmyL3Qo0rRcPc>。

只有直接阻塞构建或核心流程、令 Skill 无法达到主要目标、没有合理绕过方案，或有明确基础能力缺失时，才优先记录并考虑反馈。轻微体验差异、非核心问题、能通过 Prompt/Skill 设计绕过的问题、只存在理论影响的问题，不必为了“发现差异”而提报。小问题可以提报，但不是必需。

使用 `ideaswork skill gaps add` 时默认仅记录；只有完成上述判断后才显式加 `--report`。`--kind agent_runtime` 专用于 Agent Runtime/Framework 问题，绝不发送到平台 Tool 能力表单。
提交通道不可用（`tool_unavailable`）属于部署状态，不是上述任何一类，不记入台账、不提报。

## 新 Runtime 架构映射

Builder 本地验证平台原生 Skill 时使用固定映射：

| 平台原语 | Builder 执行入口 |
|---|---|
| `blue_list_apis` / `blue_query_api_docs` / `blue_exec_api` | Remote MCP，受当前 Context grant 限制 |
| `run_python_script` | `ideaswork runtime python` |
| `sandbox_bash` | Host Bash |
| `register_async_poll` | `ideaswork runtime wait-result` |
| `ask_user_interact`（含素材字段） | Remote MCP App；需要审批的 API 在 Remote MCP 侧拒绝执行 |

不得调用旧 `avp_local` MCP 或 Agent Service `local_rpc` 作为新 Builder 主链路。Codex Plugin 的 Runtime Core 通过 Remote MCP `create_runtime_lease` 调用远端能力：每个实际调用 Context 首次需要本地执行时取得 lease，并在有效期内复用；随包 CLI 是独立终端入口，Plugin 不读取 CLI OAuth session。

## 依赖边界

- 身份、平台执行原语、异步轮询和 harness Adapter 由仓库顶层 `ideaswork-cli` 提供。
- Builder 通过 Remote MCP 发现平台能力；构建的默认交付物是**本地草稿目录**。提交只在用户明确要求时才处理，见下文「提交（仅在被要求时）」。
- Builder 不实现 Adapter；Plugin/CLI 默认均包含 Runner、Capability、Builder，旧打包 mode 不设角色门槛。
- 制品转换由仓库顶层 `builders/` 负责；本 Skill 只生成目标无关的 Skill 源文件。

开发仓库 / standalone CLI 远端验证时可以安装并登录 CLI；Codex Plugin 模式不读取 CLI OAuth。
已有 Context 足够处理当前只读发现时复用；只有实际远端动作要求对应 mode 时才按契约切换，随后重新核对工作区、grant 和 lease。
模式切换若在旧部署产生新平台会话，保留原任务/产物关联，不能假定已合并；不为本地创作强制新建 builder Context。
Python 平台验证取得并复用实际调用 Context 的 runtime lease，不能拿旧 lease 继承权限。

## 提交（仅在被要求时）

默认终点是通过 `ideaswork skill validate` 的本地草稿目录。**用户没有要求提交/上传/推送时，不提交，也不在收尾或任何
位置提及、推荐或询问提交**；交付只说明草稿路径与校验结果。

用户明确要求提交时，才按保守策略处理，不预设通道是否可用：

- Skill 推送**不再是 MCP 工具**（`push_skill` 已移除），而是用 Runtime lease 鉴权的 HTTP 上传，与 `material upload` 同一套
  传输。先探测再授权：Plugin 调 `create_runtime_lease`（或沿用 `pull_skill` 返回的 lease），载荷里有 `skill_push_endpoint`
  才说明该账号/部署开放推送，不再用工具清单判断；CLI 直接运行 `ideaswork skill push <skill_dir> --name <name>`，它先本地
  打包校验，再取 lease 检查该字段；缺失返回 `error_code=tool_unavailable / next_action=keep_local_draft`。
- 通道不存在、scope 不足或业务权限拒绝时：保留本地草稿，如实说明这次没能提交及原因，不换身份、入口或裸 HTTP 绕过，
  不重试。提交通道的可用性属于部署状态，不属于 Skill 构建问题：不记入 gaps、不加 `--report`。
- 通道存在时，提交前检查本次用户授权、目标团队（恒为 lease 的 Context）、实际 scope 和业务写入权限（`skill.write` 不等于业务权限）。
  推送结果是**待审核版本（pending）**，不是 draft：当前运行内容不变，属主在 Studio 版本历史里接受后才生效；不 publish、
  不覆盖已发布版本、不保证返回 Studio 链接。CLI 按需使用已有 Context（没有时才切到 `builder`）并排除本地台账；
  脚本无需改写，旧草稿遗留的桥接块会在上传副本里剥离。scope 不足按服务端提示补授权；业务权限不足请用户申请，不靠重复登录。
  正式发布是独立高权限动作。
- `--set-current`（立即设为当前版本）和 `--visibility team`（新 Skill 分享给团队）会改变他人实际运行或可见的内容，服务端无法确认勾选来自用户本人：
  **Agent 不得主动添加**，默认都是 false。需要时先问用户（Plugin 用 `ask_user_interact`，CLI 在对话里问），得到明确同意才加；
  `--visibility` 只用于新建 Skill，缺省 private（仅自己）；更新已有 Skill（`--skill-id`）时永远不加 `--visibility`，改分享范围用 `update_skill`。`global` 不能通过插件或 CLI 设置。
  具体命令、结果解读与提交后的属主管理见 `sub_skill_05_generate/SKILL.md` §4。

## 阶段索引

| 阶段 | 文件 | 职责 |
|---|---|---|
| 01 | `sub_skill_01_preflight/SKILL.md` | 选模式、身份、连通性、约束 |
| 02 | `sub_skill_02_discover/SKILL.md` | 盘点业务能力并发现平台 API |
| 03 | `sub_skill_03_design/SKILL.md` | 设计可用 Skill 的结构与编排 |
| 04 | `sub_skill_04_prototype/SKILL.md` | 用低成本真实调用验证关键链路 |
| 05 | `sub_skill_05_generate/SKILL.md` | 生成可用的平台格式 Skill 并静态校验 |
| 06 | `sub_skill_06_gapreport/SKILL.md` | 收口必要问题、按归属反馈或说明无需反馈 |

两种模式都顺序完成全部阶段。06 的价值是确认是否有真正阻塞落地的问题及其准确归属；没有问题或只有已绕过的小问题时，明确记录“无需反馈”即可，不为生成报告而寻找差异。
