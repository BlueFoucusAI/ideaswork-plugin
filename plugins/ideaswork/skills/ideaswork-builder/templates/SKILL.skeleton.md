---
name: <skill-name-kebab>
description: <一句话业务目标 — 输入是什么、产出什么、覆盖哪些步骤>
---

# <skill-name> — <标题>

> **!! 关键行为约束 !!**
>
> 1. **严禁**未经用户确认就触发昂贵/不可逆操作（渲染、成片、导出、扣费类）。把这些 api_code 在此列名。
> 2. 所有异步任务用 `register_async_poll` 等待，**不在脚本内死等**。
> 3. <把本 skill 已知的平台缺口/遗留限制写在这，如「某资源只写不读，需用户显式传 id」>。

## 依赖链

```
sub_skill_01_<阶段>   — <做什么>
  └→ sub_skill_02_<阶段>  — <做什么>
       └→ sub_skill_03_<阶段> — <做什么>
```

> 每个 sub_skill 一个目录，目录名 = `sub_skill_NN_<语义>`；用 `templates/sub_skill.skeleton/` 起步。

## API 总览

> 完整 api_code 见 `api.json`。每个都应已 `blue_query_api_docs` 验证过（见 sub_skill_02 的核对规则）。

| api_code | 用途 | 类型 | 异步策略 |
|---|---|---|---|
| `<api_code>` | <用途> | exec/query | 同步 / poll: `<query_api>` / callback |

## 关键约定

- 参数来源用自然语言描述：`<当前 project_id>`、`<上一步返回的 xxx>`，**不要写 Python 伪代码**。
- 薄脚本只做纯计算，从 `templates/thin_script.template.py` 起步；直接调用运行时注入的 `call_platform_api`，不需要桥接块。
- 异步参数（delay_minutes / poll_interval / max_polls）按任务量级估，草稿里注明「上线前用真实耗时校准」。

## 待验证 API

> 还没 `blue_query_api_docs` 验证通过的 api_code 放这里（不要进 api.json，也不作 `call_platform_api` 实参）。按 sub_skill_02 的缺口分类标注：

- `<api_code>` — 用途 / 未验通原因：「未定位」（没找到对应能力）、「未授权」（当前 Context 无 grant）或「待验证」（文档未核对 / schema 未确认）

> 「不可见」不等于「平台缺失」：先核对当前 Context 的授权范围，不要断言「平台 API 未注册」。只有确认核心流程受阻且无合理绕过时，才作为平台能力问题记入问题台账，由 `sub_skill_06` 收口。
