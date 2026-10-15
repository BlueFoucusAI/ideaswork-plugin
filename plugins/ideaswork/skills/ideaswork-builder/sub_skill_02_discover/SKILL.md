# sub_skill_02_discover — 发现可用能力并核对 API 文档

## 目标

把目标业务流程拆成可实现的步骤，为每一步核对实际可用的 Skill 或 API。转化模式盘点源 Skill；
沉淀已有成果时优先整理已经采用的调用和文档证据，不重新探索全部能力；直接打样从业务步骤开始。

## 可用入口

- `browse_skills`：查看当前账号可见的已发布 Skill，先确认是否已有可复用能力。它是 Skill Catalog，不是 API 注册表。
- `blue_list_apis`：列出**当前 Context 已授权**的 `api_code` 和简要说明。它不会列出全量平台注册表；Builder Context 通常没有直接执行 API 的 grant。
- `blue_query_api_docs(api_code)`：在有 grant 的 Context 中核对候选 API 的 schema。执行前必须先查文档。
- 独立 CLI 对应命令：`ideaswork skill list`、`ideaswork api list` 和 `ideaswork api docs <api_code>`。CLI 使用自己的 OAuth Context，与 Codex Plugin 的连接分开。

旧版 `ideaswork_studio.list_skills`、`resolve_api_by_url`、`list_api_categories` 和 `browse_apis` 不在当前发行包或 Remote MCP 工具集中；不要调用这些名字，也不要用裸 HTTP 或旧 `local_rpc` 绕过授权。

## 步骤

1. **先复用已有证据。** 沉淀已有执行成果时先整理当前对话/文件中的真实调用、最终选择和结果，
   排除失败试验；证据已足够时不为重走阶段额外 browse/pull。需要查找已有 Skill 时用 `browse_skills`，
   优先复用业务语义确实相同的能力。若要查看其文件和 `api.json`，在用户选定后用 `skill_runner` Context 的 `pull_skill` 取得 checkout；不要把别的 Skill 的 API grant 当作新 Skill 的通用授权。
2. **转化模式盘点源调用。** 从已有 Skill 的指令、`api.json`、脚本和配置中整理每个外部调用的用途、HTTP method、完整 URL、参数与输出。URL 只能当作查找线索，不能据此猜 `api_code`；当前 Remote MCP 没有 URL 反查工具。
3. **按需发现与核对。** 优先复用当前 Context；缺少能力信息时调用 `blue_list_apis`，不把它当全量注册表。
   Builder 沿用现有授权机制；确需普通能力而 builder Context 未授权时，才在同一工作区使用 capability 路径，
   不要求用户切换角色。普通能力不需要靠拉取不相关 Skill 解锁，受限能力仍必须有有效 grant。
   切换远端 Context 后核对工作区、mode、grant 和 lease，保留原任务/产物关联；仅实际交接要求时切回 builder。
   旧部署仍限制直接能力时如实报告，不借切换绕过拒绝。
4. **逐个核对候选。** 已有可追溯文档时先复用；候选新增、证据缺失或 schema 可能变化时，
   对实际可查询的 `api_code` 调用 `blue_query_api_docs`，记录 schema、依赖、异步信息和参数来源。
   新远端调用仍遵守当前 Context 的 query-first，不把历史文档当成其查询凭证。只在查文档成功、且确定属于目标流程后写入草稿 `api.json`。按需读取本 Skill 的 `knowledge/<分类路径>.md`；分类知识是本地参考，不会由 Remote MCP 自动返回 `knowledge_file`。
5. **处理缺口。** 若找不到 code、没有 grant、查询被拒或 schema 不完整，分别记录为“未定位”“未授权”或“待验证”，不要直接断言“平台 API 未注册”。只有拿到实际注册表证据、确认核心流程受阻且无合理绕过时，才把它归类为平台能力问题。未知 code 不得进入 `api.json`，也不得作为 `blue_exec_api` 或 `call_platform_api` 的实参。

## 产出

- 业务步骤 → 已有 Skill 或已核对 `api_code` 的映射，附参数来源和真实文档依据。
- 源 Skill 的调用清单（仅转化模式）。
- 未定位、未授权或待验证项及其影响；只把真实阻塞记入问题台账。

继续读取 `sub_skill_03_design/SKILL.md`。
