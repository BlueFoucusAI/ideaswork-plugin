# Builder preflight

## 目标

确定构建模式、目标 Skill、可用的 IdeasWork 连接与工作区，再建立本地草稿和问题台账。

## 步骤

1. 先确认用户明确要求构建/转化/沉淀，而非仍在完成日常任务。已有执行成果时读取 `references/WORKFLOW_CAPTURE.md`，
   承接已确认需求、调用证据和产物，只问影响复用范围的缺失信息。已有具体 Skill 用 `conversion`；只有已完成流程/成果、
   需求、SOP 或想法但没有具体 Skill 用 `sampling`。明确名称、目标、输入、输出和完成判据，不重复采集已知字段。
2. 本地创作、台账和静态校验不要求远端登录、builder Context 或写入权限；纯本地任务可直接继续。
   需要远端发现/验证时，Codex Plugin 先检查 Remote MCP 连接；已有有效连接和上下文则复用。
   调用 `get_current_context` 确认工作区；**默认不切换工作区**，只有用户明确要求、或当前工作区确实无法继续时才更换，且先把“从 A → 到 B”告诉用户；需要更换团队或项目时，调用 `browse_contexts` 获取当前最新候选，再用本次结果中的名称通过 `ask_user_interact` 的 `select` 让用户明确选择。结束本轮，等待普通用户消息中的 `interaction_response`；仅在 `action=confirm` 时把所选项对应的**本次** `context_ref` 传给 `switch_context`，取消则不切换。无需提交/查询表单状态；不要使用 MCP App 展开卡片或缓存的 ref。

   `select` 表单的固定写法（`tabs` 是数组对象；`options` 是 `{label, value}` 对象数组，`value` 填该选项**本次**的
   `context_ref`；说明文字放在调用前，调用后立刻结束本轮，不再输出或调用工具）：

   ```text
   ask_user_interact(mode="form", title="选择工作区", tabs=[
     {"key": "workspace", "label": "工作区", "fields": [
       {"key": "context_ref", "type": "select", "label": "团队 / 项目", "required": true,
        "options": [{"label": "团队A / 项目1", "value": "<本次 browse_contexts 返回的 context_ref>"},
                    {"label": "团队A / 项目2", "value": "<本次 browse_contexts 返回的 context_ref>"}]}]}])
   ```

   常见错误：`tabs` 写成 JSON 字符串；`options` 写成字符串数组；tab 缺 `key` 或 `label`；使用 `name` / `default` / `choices`
   等不存在的键；用选项的 `label` 而不是 `value` 去调用 `switch_context`。
3. 本地动作只用 Host Bash、`curl` 和随包脚本（`python3`，3.10+）；**不要**寻找或安装 `ideaswork` 命令、npm 或 Go 程序。
   已有工作区可用于当前动作时不重复切 mode，不为纯本地构建建立 Context。builder 切换只用于确实要求该 mode 的远端动作；
   `context_ref` 必须来自当前用户可访问的列表，不自行构造。
4. 读取 `knowledge/CONSTRAINTS.md`。API 可用范围由远端准入决定，Builder 不自动获得垂类/策略 API 权限。
   发现阶段遵守真实可见范围；旧部署无 grant 时记录限制，不因不可见断言未注册。已有成功证据可用于本地设计，
   但不证明当前 Context 获得执行授权。无 write 不阻止本地交付。
5. 创建草稿目录。本制品**没有问题台账命令**；需要记录的阻塞或交接事项，到 `sub_skill_06` 再写成交付说明里的"遗留问题"。
   不要把 token、lease 或本地配置放进 Skill 文件。

## 产出

- `mode=conversion|sampling`，目标 Skill 的名称、核心目标、输入、输出与完成判据。
- 已确认的 IdeasWork 连接、工作区与当前可用权限。
- 草稿目录。

继续读取 `sub_skill_02_discover/SKILL.md`。
