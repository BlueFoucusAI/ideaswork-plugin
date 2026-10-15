# sub_skill_04_prototype — 低成本验证关键链路

## 目标

用当前 Context 实际授权的能力验证核心参数和结果形态，留下可复现的请求示例。验证仍以完整 Skill 为最终产出。

## 步骤

1. **先核对已有验证证据。** 沉淀入口复用真实请求、schema 和成功结果；核心参数/编排未变且证据足够的步骤
   直接记录为已有验证，不重新提交付费任务。只有提交响应、没有异步终态的步骤标为待确认；缺失或改变的关键步骤再补测。
2. 对需要新远端验证的每个 `api_code`，在实际调用 Context 先查 `blue_query_api_docs`，用返回 schema 组织 body。
   不以历史成功替代当前权限检查或 query-first；纯本地提炼/校验不要求获得远端执行权限。
3. 对最关键的 1～2 个**廉价、可逆且已获授权**的调用，用 Remote MCP `blue_exec_api(api_code, body)` 验证请求和返回。独立 CLI 对应 `ideaswork api exec <api_code> --body '<JSON>'`。只在用户已授权的范围内执行；渲染、成片导出、批量生成、发布和删除需另行获得明确同意。Remote MCP 暂无 HITL 审批通道：`need_user_approval` API 被拒绝时停止并记录阻塞，不能改用聊天确认、CLI 或其他路径绕过。
4. 异步请求只返回任务标识时，先查轮询 API 文档并确认完成条件。Codex Plugin 的本地等待使用 `ideaswork runtime wait-result`，由实际调用 Context 的 `create_runtime_lease` 提供短期 lease；命令接受 `--query-api-code`、`--params-json`、`--completion-json`、`--interval` 和 `--max-polls`。只把 lease 传给 Runtime Core parent，不写入草稿、日志或脚本。`status=lease_recovery_required` 时重新取得 lease；`timeout` 表示本段等待未完成，不表示任务失败。
5. 薄脚本需要调用 `call_platform_api` 时，用 `ideaswork runtime python` 在草稿 workspace 中验证，并传入同一 Context 的 runtime lease。该命令负责向子进程提供受限 bridge；不要直接运行 `python tools/x.py` 来验证平台调用。脚本中的打样桥接块仅用于独立 CLI/旧本地打样，`skill push` 会在上传副本中剥离。
6. 把真实请求、必要响应字段、参数来源、成本和剩余限制写进相应 sub_skill。schema 与实际行为不一致时以本次受授权调用的证据为准；仍无法验证的 API 留在「待验证 API」，不得写进可运行主链路。

## 注意事项

- 只补充验证足以证明核心链路的调用；已有足够证据不重跑。新增昂贵/批量/不可逆动作按既有规则先确认。
- 没有 grant 与平台注册表不存在是两种不同问题。先确认 Context 和权限，再判断是否需反馈。
- 异步点后的步骤只能依赖结果和已落盘文件，不能依赖上一轮内存变量。

## 产出

关键调用的真实请求/结果摘要、异步完成判据和仍需确认的限制。继续读取 `sub_skill_05_generate/SKILL.md`。
