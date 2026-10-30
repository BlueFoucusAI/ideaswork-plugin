# 心影图谱（`skill_sop.json`）

Builder 生成 Skill 时一并产出的**设计呈现文件**：让用户在宿主里看清这个 Skill 分几个阶段、每个阶段做什么。
它不是运行时编排。执行真源仍是 `SKILL.md` 与它引用的子技能文件；两者不一致时以后者为准，并同步修改图谱。

骨架见 `templates/skill_sop.skeleton.json`（三段式主链 + 用户确认回路），照它改写，不要凭记忆手编结构。
`TODO_skill_name` 与所有 `TODO` 占位必须换成真实内容。

## 位置与顶层

文件固定为 Skill 目录根下的 `skill_sop.json`（与 `SKILL.md`、`api.json` 同级），不超过 512 KB。

```json
{ "spec_version": "1.0", "title": "爆款再造", "summary": "从参考视频与创意到可验收成片", "steps": [], "edges": [] }
```

只维护 `steps` 与 `edges`。不写 `type`、`subnodes`、`parent_id`，也不写扁平索引或对齐状态。

## Step（业务阶段）

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 全局唯一、稳定；Edge 靠它引用 |
| `title` / `intent` | 是 | 面向用户的阶段名 / 该阶段要达成的目的 |
| `actions` | 是 | 阶段内的 Action；没有时写 `[]` |
| `status` | 否 | `draft` / `implemented` / `verified`，缺省 `draft` |
| `skill_key` | 否 | 对应子技能文档的完整相对路径，含扩展名：`<skill_name>/sub_skill_NN_xxx/SKILL.md`（平铺单文件写 `<skill_name>/<文件名>.md`）。不做扩展名猜测 |
| `constraints` / `input` / `output` | 否 | 设计原则 / 预期输入 / 预期产物，字符串数组，只给人看，不是运行时条件 |

## Action（阶段内动作）

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` / `title` | 是 | 全局唯一标识 / 用户可理解的动作名 |
| `status` / `intent` / `input` / `output` | 否 | 同 Step |
| `capabilities` | 否 | 计划使用的能力，每项 `type` + `ref`：`ideasworkpackage`（预制菜能力包）、`api`（平台 API code）、`script`（脚本路径，建议加 `intent`） |
| `user_interact_form` | 否 | `{ "file_key": "<skill_name>/forms/<名>.json", "mode": "form" \| "preview" }`，只引用表单文件，不复制字段；`form` 等用户提交，`preview` 只展示 |

不写 API 参数、轮询策略或运行时调用实例；`capabilities` 只表达设计意图。

## Edge（连线）

`{ "from_id", "to_id", "when"? }`：`when` 为空是主路径，有值是分支或回路（写用户能理解的条件）。
可连 Step→Step、Step→Action、Action→Step，以及**同一 Step 内**的 Action→Action；阶段间流转连到目标 Step，
不要让跨 Step 的 Action 直接连边。引用的 id 必须存在。

## 状态怎么写（Builder 约定）

- `draft`：只有设计，文件还没写；
- `implemented`：对应子技能、脚本或表单文件已生成；
- `verified`：该部分已被 sub_skill_04 的真实调用跑通。没有实测证据不写 `verified`。

## 对齐检查

宿主侧的图谱工具会在结构之外检查：`skill_key` 指向的文件、`script` 与表单文件是否存在，`api` 能力是否在 `api.json` 中。
缺失只产生警告（设计可以先于实现），逐项补齐，或向用户说明为何暂缺；结构错误（id 重复、Edge 引用不存在等）必须修复。
