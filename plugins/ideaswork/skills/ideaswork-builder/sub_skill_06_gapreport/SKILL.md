# sub_skill_06_gapreport — 问题收口与准确反馈分流

## 目标

收口**真正影响 Skill 落地**的问题，优先完成可用 Skill，而不是为了产出差异报告寻找问题。先判断问题属于 Skill 自身、平台 Tool 能力还是 Agent Runtime/Framework 能力；只对有必要的问题生成反馈计划，并准确路由。

## 前置条件

- `sub_skill_05` 完成：两种模式均已产出并校验完整 Skill。
- 本制品**没有问题台账命令**（`skill gaps` 是 CLI 的功能）：遗留问题直接写在交付说明里，不生成 `.avp_gaps.json`。

## 步骤

### 1. 只审视影响落地的问题

先回看本次构建过程中已经遇到并记下的问题（`sub_skill_03` 里标注的"待平台补能力"、`sub_skill_04` 里验证不了的 API、被拒绝的审批类 API 等）。

不要“回扫”寻找更多理论差异。只有下列情况才补充记录或考虑反馈：

- 直接阻塞 Skill 构建或核心业务流程；
- 令 Skill 无法达到主要目标；
- 没有合理的 Prompt、Skill 设计、流程调整或用户输入绕过方案；
- 有明确证据表明平台 Tool/Model/API 或 Agent Runtime/Framework 缺少必要能力或存在 Bug。

以下通常不需要补充台账，更不需要反馈：轻微体验差异、非核心问题、可轻易通过 Prompt/Skill 设计绕过的问题、理论上不同但业务无明显影响的问题。小问题可以反馈，但不是 Builder 的必做项。

### 2. 先分类，再决定是否反馈

| 归属 | 判断 | 优先处理 | 反馈入口 |
|---|---|---|---|
| Skill 自身问题 | Prompt、指令、工具选择、参数映射、编排、状态传递或验证不充分 | 直接修复 Skill；可用 `--kind skill_issue` 记录修复说明 | 不提报 |
| 平台 Tool 能力问题 | Tool、Model、API、必要参数、文档或 API 行为缺失/错误 | 先确认没有合理绕过且影响核心目标 | [平台能力反馈表单](https://bluefocus.feishu.cn/share/base/form/shrcnB3SRCUsabcsTcyiS0V4O8g) |
| Agent Runtime / Framework 能力问题 | Skill 设计合理，但执行层不支持/错误实现 Sub Agent、上下文传递、Tool 回调、异步恢复或运行时逻辑 | 先确认不是 Skill 编排问题且没有合理绕过 | [Agent 能力反馈表单](https://bluefocus.feishu.cn/share/base/form/shrcnpGPjWDbCjPmyL3Qo0rRcPc) |

不要把 Runtime 问题错记为 `missing_api`、`missing_capability` 或 `schema_gap`，也不要把 Skill 自身问题外推成平台/Runtime 缺陷。

### 3. 把必要的问题写成"遗留问题"条目

每条只在"阻塞 + 无合理绕过 + 归属明确"后才**值得提给用户考虑反馈**；非阻塞小问题可以写下来，但绝不是必做项。每条包含：

| 字段 | 内容 |
|---|---|
| 类别 | `skill_issue`（Skill 自身，已修复或仅记录）/ `missing_api`、`missing_capability`（平台 Tool 能力）/ `agent_runtime`（Agent Runtime/Framework） |
| 标题 | 一句话：缺什么 / 坏了什么 |
| 期望 | 希望平台或 Runtime 做到什么 |
| 优先级 | 默认 P2；只有真实挡住主链路才用 P0/P1，避免优先级通胀 |
| 影响步骤 | 核心 Skill 的哪一步 |
| 证据 | 可复现的请求/返回/检索结果或 Runtime 行为；不含 token、完整响应体或用户敏感数据 |
| 绕过 | 有就写，没有写"无" |
| 是否阻塞 | 是 / 否 |

平台 Tool 类还要写一级域（如 `PLATFORM_INFRA`）和二级域；`agent_runtime` 类**不得**套用平台 Tool 能力表单的字段。
Skill 自身问题只修复并记录"已在 Skill 中修复"，不提报。

### 4. 生成摘要并按归属分流

在交付说明里按三组整理：**平台 Tool/Model/API**、**Agent Runtime/Framework**、**Skill 自身 / 已绕过 / 仅记录**。不生成额外文件
（本制品没有 `render` / `submit-plan` 命令）。

- 平台能力问题：把[平台能力反馈表单](https://bluefocus.feishu.cn/share/base/form/shrcnB3SRCUsabcsTcyiS0V4O8g)链接和条目正文交给用户，由用户决定是否自己提交。
- Agent Runtime 问题：把[Agent 能力反馈表单](https://bluefocus.feishu.cn/share/base/form/shrcnpGPjWDbCjPmyL3Qo0rRcPc)链接和条目正文交给用户；
  **不得复用平台 Tool 能力表单的 payload 或字段**。
- Skill 自身、已绕过或仅记录的问题不提交外部表单。

**不自行提交任何外部表单。** 提报是写操作：先把条目逐条交给用户，获得对本次条目的明确同意，且由用户自己提交；本制品不提供代为提交的通道。

### 5. 收尾汇报

向用户交付：

1. 可用 Skill 的**本地草稿路径**与本地自检结果，并说明是否仍有核心路径阻塞发布。用户没有要求过提交，就不提及提交；只有提交实际发生过，才附服务端返回的 Skill ID、版本和版本状态（默认是待审核版本，需属主在 Studio 版本历史接受；推送不返回 `studio_url`）。
2. 遗留问题的结论：核心目标是否可落地、是否有真正阻塞项。
3. 若有待反馈项：逐条说明它属于平台 Tool 还是 Agent Runtime，以及对应表单链接；是否提交由用户决定。
4. 若无待反馈项：明确说明“没有阻塞落地的问题，无需反馈”。这是有效结论。

## 注意事项

- “感觉平台不支持”或“理论上有差异”不构成反馈证据；至少给出真实请求、API 检索、Runtime 行为或可复现报错。
- 提交通道不可用（lease 载荷没有 `skill_push_endpoint`）属于部署状态，不构成平台能力或 Runtime 反馈项，不记入遗留问题、不提报。
- 自由文本 → 结构化内容通常应先考虑薄脚本 + 通用 LLM，不因没有业务专用 API 就判为平台缺能力。
- 不在摘要或表单中写 token、完整响应体或用户敏感数据；证据只保留必要的请求摘要、报错与步骤上下文。

## 产出

交付说明里的遗留问题清单（可为空）+ 一次以“Skill 是否实际可落地”为中心的收尾汇报。两种模式到此结束。
