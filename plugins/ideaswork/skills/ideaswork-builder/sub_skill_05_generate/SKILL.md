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

- **本地通过不等于平台一定通过**：平台另有静态安全审查，本地不执行。以 `ideaswork skill validate` 的禁用项检查
  和 `knowledge/CONSTRAINTS.md` 为准，不要用 `os.environ`、第三方包、网络服务等。
- 旧草稿里的 `# === avp_local 打样桥接` 块已不需要，删除即可；留着不会出错，`skill validate` 仍接受它，
  `skill push` 会在**上传副本**里剥离（残缺、重复或顺序错误的标记会被拒绝打包，需修复或删除）。

### 3. 本地校验

```bash
ideaswork skill validate <草稿目录>
```

修复全部 FAIL。核对 `api.json` 是用途说明 dict，`__` 前缀键不计入 API，业务 code 都已查过文档、核心路径没有未授权或待验证的 API；对关键调用保留 sub_skill_04 的真实请求示例。静态校验不会证明平台 API 实际可调用。

### 4. 提交团队 draft（仅在用户明确要求时；不是本地交付前提）

先交付草稿路径、名称、说明和静态校验结果，到此本地交付已完整。**用户没有要求上传/提交/推送时，跳过本节，
也不提及、推荐或询问提交。** 用户请求“发布”也不能让 push 自动变为正式发布。

用户明确要求后，**先探测，再授权**：确认提交通道真实存在，再向用户展示目标团队和提交范围并取得本次上传授权。

- **Codex Plugin 主链路**：保持 Plugin 的 OAuth 身份，不默认改用独立 CLI。看当前 MCP 工具清单有无 `push_skill`；
  没有就停止本节，保留本地交付并说明限制，不臆造工具、不借 CLI 身份绕过。
  有则按它的实际 schema/大小上限构造 zip：只包含 Skill 源文件（若有旧桥接块则在上传副本里剥离），
  排除 `.avp_gaps.json`、`SKILL_BUILD_FINDINGS.md`、`__skill_meta.json`、构建说明、凭据、缓存和测试产物；保留本地源文件。
  残缺/重复/顺序错误的桥接标记先修复，不上传符号链接、越界路径或未经检查的 archive。用真实团队 Context 提交。
- **独立 CLI 入口**：仅当前任务明确使用并授权 CLI 时，沿用它的 OAuth 和同一个 `--task`。`skill push` 自己先本地打包校验、
  再探测工具，探测不到时在改动任何 Context 之前返回 `tool_unavailable / keep_local_draft`：

```bash
ideaswork skill push <草稿目录> --name <skill-name> --category <category> --description "<说明>" --json --task <task>
```

  沿用当前已确认的团队；需要换团队时才先 `context list --json --task <task>` 让用户确认本次候选，
  再 `context use <本次确认的context_ref> --mode builder --json --task <task>`。
  CLI push 排除本地台账和缓存（旧草稿里的桥接块也会在上传副本中剥离）。

**不可用**（`tool_unavailable`，或 Plugin 工具清单里没有 `push_skill`）：保留本地草稿，如实说明这次没能提交，
草稿在 <路径>。提交通道的可用性属于部署状态，不是 Skill 构建问题：**不记入 gaps、不 `--report`**，
不重试，不换身份、入口或裸 HTTP 绕过。

**结果与失败**：只按真实返回记录 draft ID、名称、状态、API codes 和 `publish_required`。
`push_skill` 不自动 publish、覆盖正式版本或保证返回 Studio 链接。名称冲突、非团队空间或权限拒绝时保留草稿。
缺少 OAuth scope 按服务端实际补充授权提示处理；有 scope 但业务权限不足应申请业务权限，不反复登录。
Plugin/CLI 凭据不互换，不自动切通道重试；没有服务端确认就不能声称已提交。

### 5. 收口

进入 `sub_skill_06_gapreport`，带上本地草稿路径；仅当服务端实际接受了提交，才一并带上返回的 draft ID、名称、状态和 `publish_required`。正式发布由具备权限的用户在平台另行操作。

## 产出

通过静态校验的本地 Skill 草稿。只有实际提交成功时才附服务端返回的 Builder draft 元数据；没有服务端返回就只报告本地草稿，不声称已交接或已发布。
