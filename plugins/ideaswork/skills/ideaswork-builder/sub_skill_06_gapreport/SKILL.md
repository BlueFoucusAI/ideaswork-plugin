# sub_skill_06_gapreport — 问题收口与准确反馈分流

## 目标

收口**真正影响 Skill 落地**的问题，优先完成可用 Skill，而不是为了产出差异报告寻找问题。先判断问题属于 Skill 自身、平台 Tool 能力还是 Agent Runtime/Framework 能力；只对有必要的问题生成反馈计划，并准确路由。

## 前置条件

- `sub_skill_05` 完成：两种模式均已产出并校验完整 Skill。
- 台账 `<草稿目录>/.avp_gaps.json` 已在 `sub_skill_01` 建好；它可以为空。

## 步骤

### 1. 只审视影响落地的问题

先看已有记录：

```bash
ideaswork skill gaps list --draft <草稿目录>
```

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

### 3. 记录必要条目

`gaps add` 默认只记录。默认在“阻塞 + 无合理绕过 + 归属明确”后才显式加 `--report`。非阻塞小问题也可在明确说明实际价值后酌情加 `--report`，但绝不是必做项。每条都要有可复现证据、影响步骤和绕过情况。

平台 Tool/API 示例：

```bash
ideaswork skill gaps add --draft <草稿目录> --kind missing_api \
    --title "<缺失的 Tool/API>" --expect "<需要的平台能力>" \
    --priority P1 --domain PLATFORM_INFRA --sub-domain <二级域> \
    --where "<核心 Skill 步骤>" --evidence "<请求/返回/检索证据>" \
    --blocking --workaround "无" --report
```

Agent Runtime/Framework 示例：

```bash
ideaswork skill gaps add --draft <草稿目录> --kind agent_runtime \
    --title "<Runtime/Framework 能力限制或 Bug>" --expect "<需要的执行能力>" \
    --priority P1 --where "<核心 Skill 步骤>" \
    --evidence "<可复现的 Runtime 行为/报错>" \
    --blocking --workaround "无" --report
```

Skill 自身问题只修复或记录，不加 `--report`：

```bash
ideaswork skill gaps add --draft <草稿目录> --kind skill_issue \
    --title "<已修复的 Skill 编排/Prompt 问题>" --expect "<修复后的正确行为>" \
    --where "<步骤>" --workaround "已在 Skill 中修复"
```

`--priority` 默认 P2；只有真实挡住主链路才用 P0/P1，避免优先级通胀。

### 4. 生成摘要并按归属分流

```bash
ideaswork skill gaps render --draft <草稿目录>
ideaswork skill gaps submit-plan --draft <草稿目录>
```

`render` 生成 `<草稿目录>/SKILL_BUILD_FINDINGS.md`，分为平台 Tool/Model/API、Agent Runtime/Framework、以及 Skill 自身/已绕过/仅记录三组。

- 平台能力问题使用原有平台能力表单。若有 `lark-cli`，`submit-plan` 会给出按真实平台表单字段构造的计划；没有则交付摘要和表单链接。不要为了提报安装 `lark-cli`。
- Agent Runtime 问题使用新 Agent 能力表单。`submit-plan` 会单独给出该表单链接和条目正文；提交前先读取该表单的实际字段，**不得复用平台 Tool 能力表单的 payload 或字段**。
- Skill 自身、已绕过或仅记录的问题不提交外部表单。

提报是写操作。即使条目已经标记 `--report`，也必须先把计划逐条交给用户，获得对本次条目的明确同意才可提交。

### 5. 收尾汇报

向用户交付：

1. 可用 Skill 草稿路径与服务端返回的 Builder draft ID/状态（如已交接），并说明是否仍有核心路径阻塞发布；`push_skill` 不返回 `studio_url`。
2. `SKILL_BUILD_FINDINGS.md` 路径与结论：核心目标是否可落地、是否有真正阻塞项。
3. 若有待反馈项：逐条说明它属于平台 Tool 还是 Agent Runtime，已标记/已提交/待用户确认的状态，以及对应表单。
4. 若无待反馈项：明确说明“没有阻塞落地的问题，无需反馈”。这是有效结论。

## 注意事项

- “感觉平台不支持”或“理论上有差异”不构成反馈证据；至少给出真实请求、API 检索、Runtime 行为或可复现报错。
- 自由文本 → 结构化内容通常应先考虑薄脚本 + 通用 LLM，不因没有业务专用 API 就判为平台缺能力。
- 不在摘要或表单中写 token、完整响应体或用户敏感数据；证据只保留必要的请求摘要、报错与步骤上下文。

## 产出

`<草稿目录>/SKILL_BUILD_FINDINGS.md` + （可选）按归属生成的反馈计划/回执 + 一次以“Skill 是否实际可落地”为中心的收尾汇报。两种模式到此结束。
