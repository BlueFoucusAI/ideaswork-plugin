# sub_skill_05_generate — 生成 Skill 草稿并交接 Builder draft

## 目标

把设计与验证结果落成一份可运行的平台格式 Skill，完成本地静态校验，再按用户授权交接为团队 Builder draft。`push_skill` 不会自动发布。

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

用 `templates/SKILL.skeleton.md`、`templates/api.skeleton.json` 和 `templates/thin_script.template.py` 作为结构参考。Agent 负责业务编排；脚本只做必要的计算或单次平台调用。不要把 CLI、`avp_local` 包、Adapter、token、缓存或问题台账复制进草稿。

`api.json` **统一用 dict，不生成字符串数组**。每个已查文档并验证过的 code 写一句实际用途；`__` 前缀键（如 `__desc_01`）用于分组/注释，不计入白名单。转化旧数组时逐项补用途，不把注释当成 API：

```json
{
  "__desc_01": "── 能力发现 ──",
  "model_list": "列出可用模型，供流程选择生成能力"
}
```

示例 code 只有真实查文档并验证后才能用于草稿。`api.json` 是 DB `api_codes` 的唯一文件来源，不另交一份独立白名单；DB 字段与工具返回的 `api_codes` 数组不因此改为 dict。文件不能为 `{}`；若确实不调用平台 API，写 `{"__desc": "本技能不依赖平台 API"}`。所有用途/说明值必须是非空字符串；删除模板占位符和 `__comment_*` 模板说明，实际分组注释可保留。

### 2. 处理打样桥接块

薄脚本可保留模板中的标记块，让独立终端打样时使用 `avp_local`：

```python
# === avp_local 打样桥接：迁移到平台时整块删除（平台运行时注入 call_platform_api）===
try:
    import avp_local as _ap; _ap.setup()
    call_platform_api = _ap.call_platform_api
except ImportError:
    pass
# === 打样桥接结束 ===
```

脚本正文继续使用 `call_platform_api(api_code, body)`。`ideaswork skill push` 只在**上传副本**中剥离完整标记块，保留本地源文件；标记缺失、重复或顺序错误会拒绝打包。平台运行时负责注入同名函数。

### 3. 本地校验

```bash
ideaswork skill validate <草稿目录>
```

修复全部 FAIL。核对 `api.json` 是用途说明 dict，`__` 前缀键不计入 API，业务 code 都已查过文档、核心路径没有未授权或待验证的 API；对关键调用保留 sub_skill_04 的真实请求示例。静态校验不会证明平台 API 实际可调用。

### 4. 按需提交团队 draft（不是本地交付前提）

先交付草稿路径、名称、说明和静态校验结果。仅用户明确要求上传/提交时，展示目标团队和提交范围，
取得本次上传授权；检查当前入口是否真实提供 `push_skill`、实际 scope 和业务写入权限。
本地创作不要求 write；用户请求“发布”也不能让 push 自动变为正式发布。

**Codex Plugin 主链路**：保持 Plugin 的 OAuth 身份，不默认改用独立 CLI。
若 `push_skill` 可用，按它的实际 schema/大小上限构造 zip：只包含 Skill 源文件，剥离上传副本的完整打样桥接标记块，
排除 `.avp_gaps.json`、`SKILL_BUILD_FINDINGS.md`、`__skill_meta.json`、构建说明、凭据、缓存和测试产物；保留本地源文件。
缺失/重复/顺序错误的桥接标记先修复，不上传符号链接、越界路径或未经检查的 archive。用真实团队 Context 提交。
Tool 未注册或无法按契约构造受检 archive 时，保留本地交付并说明限制，不臆造工具、不借 CLI 身份绕过。

**独立 CLI 入口**：仅当前任务明确使用并授权 CLI 时，沿用它的 OAuth 和同一个 `--task`：

```bash
ideaswork context list --json --task <task>
ideaswork context use <本次确认的团队context_ref> --mode builder --json --task <task>
ideaswork skill push <草稿目录> --name <skill-name> --category <category> --description "<说明>" --json --task <task>
```

已有正确团队可复用；只在远端契约要求时切换 mode。CLI push 会剥离上传副本的打样桥接块并排除本地台账和缓存。

**结果与失败**：只按真实返回记录 draft ID、名称、状态、API codes 和 `publish_required`。
`push_skill` 不自动 publish、覆盖正式版本或保证返回 Studio 链接。名称冲突、非团队空间、Tool 不可用或权限拒绝时保留草稿。
缺少 OAuth scope 按服务端实际补充授权提示处理；有 scope 但业务权限不足应申请业务权限，不反复登录。
Plugin/CLI 凭据不互换，不自动切通道重试；没有服务端确认就不能声称已提交。

### 5. 收口

交接后记录服务端实际返回的 draft ID、名称、状态和 `publish_required`，连同本地草稿路径进入 `sub_skill_06_gapreport`。正式发布由具备权限的用户在平台另行操作。

## 产出

通过静态校验的本地 Skill 草稿；如已获授权并上传，附实际返回的 Builder draft 元数据。没有服务端返回就只报告本地草稿，不声称已交接或已发布。
