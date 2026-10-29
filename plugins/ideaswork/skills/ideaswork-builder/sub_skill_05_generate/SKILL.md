# sub_skill_05_generate — 生成 Skill 草稿并本地交付

## 目标

把设计与验证结果落成一份可运行的平台格式 Skill，完成本地静态校验并交付本地草稿目录。远端提交只在用户明确要求时才处理，见 §4。

## 步骤

### 1. 生成目标无关的 Skill 源文件

在工作目录生成完整 Skill：

```text
<skill-name>/
├── SKILL.md                    # frontmatter(name/description)、端到端流程、关键约束
├── api.json                    # api_code → 一句话用途说明的 dict；__ 前缀键为注释
├── sub_skill_01_xxx/SKILL.md   # 按业务阶段拆分
└── tools/*.py                  # 仅在确有计算或 prompt 工程时使用
```

用 `templates/SKILL.skeleton.md`、`templates/api.skeleton.json` 和 `templates/thin_script.template.py` 作为结构参考。Agent 负责业务编排；脚本只做必要的计算或单次平台调用。不要把 CLI、`avp_local` 包、Adapter、token、缓存或问题台账复制进草稿，也不要在脚本里写桥接/兜底代码。

`api.json` **统一用 dict，不生成字符串数组**。每个已查文档并验证过的 code 写一句实际用途；`__` 前缀键（如 `__desc_01`）用于分组/注释，不计入白名单。转化旧数组时逐项补用途，不把注释当成 API：

```json
{
  "__desc_01": "── 能力发现 ──",
  "model_list": "列出可用模型，供流程选择生成能力"
}
```

示例 code 只有真实查文档并验证后才能用于草稿。`api.json` 是 DB `api_codes` 的唯一文件来源，不另交一份独立白名单；DB 字段与工具返回的 `api_codes` 数组不因此改为 dict。文件不能为 `{}`；若确实不调用平台 API，写 `{"__desc": "本技能不依赖平台 API"}`。所有用途/说明值必须是非空字符串；删除模板占位符和 `__comment_*` 模板说明，实际分组注释可保留。

### 2. 脚本本地与平台是同一份代码

薄脚本**直接调用** `call_platform_api(api_code, body)`：它是运行时注入的内置函数，不 import、不加桥接块、不需要迁移改写。
本地用 `ideaswork runtime python` 验证时，Runtime Core 注入的同名函数与平台行为一致，所以验证过的脚本可以原样上传。
不要直接 `python tools/x.py`（裸跑没有注入，会 `NameError`）。

- **本地通过不等于平台一定通过**：平台另有静态安全审查，本地不执行（`skill validate` 已覆盖推送闸门的内容校验，包括 `skill_sop.json` 的结构与引用）。以 `ideaswork skill validate` 的禁用项检查
  和 `knowledge/CONSTRAINTS.md` 为准，不要用 `os.environ`、第三方包、网络服务等。
- 旧草稿里的 `# === avp_local 打样桥接` 块已不需要，删除即可；留着不会出错，`skill validate` 仍接受它，
  `skill push` 会在**上传副本**里剥离（残缺、重复或顺序错误的标记会被拒绝打包，需修复或删除）。

### 3. 本地校验

```bash
ideaswork skill validate <草稿目录>
```

修复全部 FAIL。核对 `api.json` 是用途说明 dict，`__` 前缀键不计入 API，业务 code 都已查过文档、核心路径没有未授权或待验证的 API；对关键调用保留 sub_skill_04 的真实请求示例。静态校验不会证明平台 API 实际可调用。

### 4. 提交到团队（仅在用户明确要求时；不是本地交付前提）

先交付草稿路径、名称、说明和静态校验结果，到此本地交付已完整。**用户没有要求上传/提交/推送时，跳过本节，
也不提及、推荐或询问提交。** 用户请求“发布”也不能让 push 自动变为正式发布。

用户明确要求后，**先探测，再授权**：确认提交通道真实存在，再向用户展示目标团队和提交范围并取得本次上传授权。
Skill 推送**不再是 MCP 工具**：它是用 Runtime lease 鉴权的 HTTP 上传（`/mcp/runtime/lease/skills/push`，zip ≤ 20 MiB），
和 `material upload` 同一套传输；目标团队恒为 lease 的 Context，调用方不能指定。zip 由 `skill push` 自己打包
（只含 Skill 源文件；排除 `.avp_gaps.json`、`SKILL_BUILD_FINDINGS.md`、`__skill_meta.json`、缓存和构建台账；
旧桥接块在上传副本里剥离，残缺/重复/顺序错误的标记先修复；拒绝符号链接与越界路径），Agent 不手工构造 archive。

- **Codex Plugin 主链路**：保持 Plugin 的 OAuth 身份，不默认改用独立 CLI。先 `get_current_context` 确认是有团队的 Context
  （已有 active context 就沿用，不为推送强改 mode；没有才 `switch_context`），再调 `create_runtime_lease`。
  载荷里没有 `skill_push_endpoint` 就停止本节，保留本地交付并说明限制，不臆造工具、不借 CLI 身份绕过。有则：

```bash
sh <plugin_root>/runtime/bin/ideaswork skill push <草稿目录> --name <skill-name> \
  --runtime-endpoint <runtime_endpoint> --runtime-lease-stdin --json
```

  `runtime_lease` 只经 stdin 传入（与 Runner 的 `material upload` 相同），不写入文件、日志或命令行。
- **独立 CLI 入口**：仅当前任务明确使用并授权 CLI 时，沿用它的 OAuth 和同一个 `--task`。`skill push` 自己先本地打包校验，
  再取 lease 并检查 `skill_push_endpoint`，缺失时在改动任何 Context 之前返回 `tool_unavailable / keep_local_draft`：

```bash
ideaswork skill push <草稿目录> --name <skill-name> --category <category> --description "<说明>" --json --task <task>
```

  沿用当前已确认的团队和已有 Context（没有 active context 时才切到 `builder`）；需要换团队时才先 `context list --json --task <task>`
  把“从 A → 到 B”和候选告诉用户并得到同意，再 `context use <本次确认的context_ref> --mode builder --confirm-switch --json --task <task>`（不要因推送失败而自行换团队）。

两种入口的其余选项相同：`--skill-id <id>` 给自己名下的已有 Skill 加新版本（此时 `--name` 可省，仅属主、限同一团队，不靠重名覆盖）；
`--category`（缺省由服务端定为 general）、`--description`、`--version`（semver；缺省为下一个补丁号，新建为 1.0.0）、`--changelog`。

**`--set-current` 与 `--visibility` 必须先问用户，Agent 不得主动添加**：`--set-current` 立即把该版本设为当前版本，
`--visibility team` 让新 Skill 被接受发布后对同团队可见；二者都会改变他人实际运行或可见的内容，服务端无法确认勾选来自用户本人。
默认都不传（版本待审核、分享范围 private 仅自己）；用户没有明确选择就一个都不传（Plugin 用 `ask_user_interact` 询问，CLI 在对话里询问）。
`--visibility` 只用于**新建** Skill（`private` 或 `team`），它只是写入分享范围，被接受发布前他人仍看不到；更新已有 Skill
（`--skill-id`）时永远不加 `--visibility`，改分享范围用 `update_skill`。`global` 不能通过插件或 CLI 设置。

**不可用**（`tool_unavailable`，或 lease 载荷没有 `skill_push_endpoint`）：保留本地草稿，如实说明这次没能提交，
草稿在 <路径>。提交通道的可用性属于部署状态，不是 Skill 构建问题：**不记入 gaps、不 `--report`**，
不重试，不换身份、入口或裸 HTTP 绕过。

**结果**：成功返回 `status`（`version_pending` 或 `version_active`）、`skill`（id/name/created/status/scope/version）、
`version`（id/version/status）、`api_codes`、`file_count`、`set_current`、`visibility`、`publish_required`、`warnings`。只按真实返回汇报：
- 默认是**待审核版本（pending）**，不是 draft：当前运行内容没有变，属主在 Studio 版本历史里接受后才生效；新建 Skill 另有一条
  `draft` 占位行，可在「我的 Skill」里看到并拉取，但未被接受前不是已发布 Skill。不 publish、不覆盖正式版本、不保证返回 Studio 链接。
- `set_current.error` 非空表示“设为当前版本”失败而推送本身成功：待审核版本已保留且版本号已占用，**不整体重试**，
  告诉用户到版本历史处理，或经用户确认后用 `manage_skill_version` 重试设为当前。
- 分享范围只在新建时由 `--visibility` 决定，缺省 private（仅自己）；`skill.scope` 为 `private` 时不要说“团队已可用”，如实告诉用户目前只有自己能用。

**失败**（`error_code`，看码不看 HTTP 状态）：
- `invalid_archive` / `validation_failed` / `invalid_options` / `invalid_name`：草稿或参数问题，按提示修复后重推。
- `skill_exists` / `version_exists`：名称已被占用 / 版本号已存在；自己名下的同名 Skill 改用 `--skill-id`，否则换名或换版本。不要覆盖。
- `forbidden` / `team_mismatch` / `skill_not_found`：无权限、Skill 属于其他团队、Skill 不存在；让用户确认团队与 Skill，
  `team_mismatch` 需切回对应团队的 Context 后重新取 lease。保留草稿。
- `runtime_lease_*`（过期、额度用尽、scope 不足）/ `push_requires_team`（当前 Context 没有团队）：按 `next_action` 重新获取 lease 或补授权/换团队。
- `storage_failed`（`retryable=true`）：服务端已回滚，可稍后重试一次。
- **`push_result_unknown`**（退出码 6，网络中断或网关 5xx 之后）：结果未知，**不自动重试**，先让用户在「我的 Skill」或 Studio 版本历史里
  确认是否已生成版本，再决定；没有服务端确认就不能声称已提交。OAuth CLI 可用 `ideaswork skill versions <skill_id> --json` 直接查；
  Plugin 用 Remote MCP 的 `list_skill_versions`。
- **`validation_failed`**（退出码 1）：推送前的本地闸门或服务端校验未通过，消息里逐条列出问题（含 `skill_sop.json` 的字段路径）；修好草稿再推，不要改版本号。
- **`push_network_unreachable`**（退出码 1，`retryable=true`）：连接都没建立，请求**没有发出**，草稿与线上版本不变；不要去查版本历史，
  也不要换版本号乱试。多半是沙箱没有网络：向用户说明，申请放开该命令的网络权限后原样重推一次。
缺少 OAuth scope 按服务端实际补充授权提示处理；有 scope 但业务权限不足应申请业务权限，不反复登录。
Plugin/CLI 凭据不互换，不自动切通道重试。

**提交之后：属主管理（Plugin 的 Remote MCP 工具，仅在用户要求时使用）**

| 工具 | 用途 |
|---|---|
| `list_skill_versions` | 列出自己 Skill 的版本及状态（pending 待审核 / active 当前 / superseded 已归档 / rejected 已拒绝） |
| `manage_skill_version` | `action=set_current`：接受待审核版本，或回滚到已归档/已拒绝版本；`action=reject`：拒绝待审核版本（可附 `reason`） |
| `update_skill` | 展示信息（`display_name`、`description`、`category`、`icon`）、`visibility`（private 仅自己 / team 团队，不能设 global）、`derivable`、`linked_skill_ids` |

- 它们按 `skill_id` 做属主校验，不要求 Context；`skill_id` 来自推送结果或「我的 Skill」。
- 凡影响他人的变更——`set_current`、`visibility`、`derivable`、`linked_skill_ids`——**必须先向用户说明版本和影响并取得明确确认**
  （`ask_user_interact` 或对话），确认前不调用。展示信息的修改不需要额外确认。
- `derivable`（允许他人在 Web 技能中心派生/下载）**不限制 `pull_skill`**：目录里可见的 Skill 同团队成员始终可以拉取，
  不要把它当成访问控制告诉用户。
- 刻意不提供：发布状态与可见范围、API 白名单、目录可见性开关、删除；正式发布仍是 Studio 里的独立操作。
- `browse_skills` 的 Catalog App 在「我的 Skill」下列出自己的全部 Skill（含草稿、已禁用），卡片上的「管理」把选择交还给 Agent
  （收到 `skill_manage_requested` 的用户消息）：用上面的工具继续，同样先确认。
- CLI 暂无对应的管理命令；CLI 用户要接受/回滚版本，请指引到 Skill Studio 的版本历史。

### 5. 收口

进入 `sub_skill_06_gapreport`，带上本地草稿路径；仅当服务端实际接受了提交，才一并带上返回的 Skill ID、名称、版本、版本状态（pending/active）和 `publish_required`。属主接受版本与正式发布由具备权限的用户在平台另行操作。

## 产出

通过静态校验的本地 Skill 草稿。只有实际提交成功时才附服务端返回的 Skill/版本元数据（默认是待审核版本）；没有服务端返回就只报告本地草稿，不声称已交接或已发布。
