# knowledge/ — 平台分类知识库

本目录存放**打样期**给 agent 看的平台侧知识。分两类：

| 文件 | 性质 | 何时读 |
|---|---|---|
| `CONSTRAINTS.md` | 全局约束（写脚本必读） | sub_skill_01 一次性读入 |
| `SKILL_SOP.md` | 心影图谱 `skill_sop.json` 的结构与写法 | sub_skill_05 生成图谱时读 |
| `<CATEGORY>.md`（镜像 category 层级） | 某分类的隐含知识 | **用到该分类能力时才读**（渐进式披露） |

## 分类知识：目录即 category 层级

平台 API 分类形如 `AI_INFRA/TEXT2VIDEO`、`PLATFORM_INFRA/PROJECT`。知识文件按同样层级落盘：

```
分类 A/B  →  knowledge/A/B.md
```

例：`AI_INFRA/TEXT2VIDEO` → `knowledge/AI_INFRA/TEXT2VIDEO.md`。

`CONSTRAINTS.md` 是 Builder 的全局约束。执行语义对照位于
`../../ideaswork-runner/references/EXECUTION_PARITY.md`。

## 渐进式披露（按需加载，禁止预读）

- 在 `sub_skill_02` 得到已授权 `api_code` 并查文档后，若能确定分类且本目录有对应知识文件，**先读对应文件再设计该分类的调用**。
- **只加载正在使用的分类知识**，不要把 `knowledge/` 下所有文件一次性读进来——这违背渐进式披露、徒增上下文。
- 没有对应知识文件时，按已授权 API 的 description 与 `blue_query_api_docs` 设计；不要臆造不存在的 `knowledge_file` 返回字段。

## 内容原则

- 只写**平台侧隐含、description 里零散或读不全**的信息（字段语义陷阱、跨接口依赖、易错默认值、异步轮询要点）。
- 一切以**实测**为准：字段/枚举以 `blue_query_api_docs` 的 schema 与 `model_list` 为准，不臆造；不确定的标注「待确认」。
- 不重复 description 已说清的内容。

## 新增一个分类知识

1. 从已授权 API 文档或可信的现有 Skill 确认 category 名；Remote MCP 不提供旧版全量分类浏览工具。
2. 在 `knowledge/<分类各段>.md` 建文件（目录不存在先建）。
3. 内容基于该分类各 api_code 的真实 `blue_query_api_docs` 输出撰写。
4. 在相关 sub_skill 中引用该路径，使用时按需读取；不会由 Remote MCP 自动提示本地文件。
