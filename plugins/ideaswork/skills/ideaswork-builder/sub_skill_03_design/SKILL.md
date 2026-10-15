# sub_skill_03_design — API-First 设计流程与 sub_skill 拆分

## 目标

把业务流程设计成符合平台 API-First 原则的方案：明确每步是「Agent 直接调 API」还是「薄脚本」，并拆成有序 sub_skill。

## 前置条件

- `sub_skill_02` 完成，已有 API 清单（含 schema/依赖/异步策略）。

## 步骤

### 1. 逐步判定：直接 API 还是薄脚本

从已有成果沉淀时先提炼最终采用的成功路径，把具体 ID、路径和数量改成输入或结果引用，保留确定的业务规则。
失败试验不串进主流程；保留必要异常处理，明确未验证的分支。已有结构合理就复用，不为构建重新生成产物。

对每个步骤套用判定标准（详见 `knowledge/CONSTRAINTS.md`）：

| 步骤性质 | 归属 |
|---|---|
| 创建/查询/更新业务对象（CRUD 类平台 API） | **Agent 直接调** `blue_exec_api`，不写脚本 |
| 需要 prompt 工程的 LLM 文本/JSON 生成 | **薄脚本** `gen_xxx.py` |
| TTS 语音合成 | **薄脚本** `gen_voice.py` |
| 纯数据处理/格式转换 | 薄脚本 或 Agent 直接处理 |
| 等待异步任务 | 平台 `register_async_poll`，**不在脚本里轮询** |

> 经验法则：**有 prompt 工程/计算 → 薄脚本；纯 CRUD → 直接 `blue_exec_api`**。

> **当某业务步骤没有直接的 CRUD API 时**，先判断能否通过当前 Context 已授权的通用 LLM 能力和薄脚本完成。`api_code` 必须来自实际授权列表并查过文档，不能用 `"*_llm_chat"` 这样的模式猜测。若只是当前 Context 看不到 API，先记录权限缺口，不据此断言平台缺能力。

> 只有确认不是 Skill 的 Prompt/编排可解决、不是薄脚本+通用 LLM 可解决，且缺失会阻塞核心目标并无合理绕过时，才将它归为**平台 Tool/Model/API 能力问题**，在草稿中标注「待平台补能力」并记录：

```bash
ideaswork skill gaps add --draft <草稿目录> --kind missing_capability \
    --title "<一句话：平台缺什么能力>" --expect "<希望平台能做到什么>" \
    --priority P1 --domain <一级域> --sub-domain <二级域> --blocking \
    --where "<本 skill 哪一步>" --workaround "无" \
    --evidence "<已授权能力、文档和真实调用为何无法覆盖>" --report
```

**判定门槛**：只有在确认不是权限范围限制、已授权通用能力和薄脚本也无法解决、且核心目标受阻时，才把问题归为 `missing_capability`。


### 2. 拆 sub_skill

按执行顺序拆成 `sub_skill_01_xxx`、`sub_skill_02_xxx`…，每个 sub_skill 是一个内聚的业务阶段。明确每步的输入来源（上一步产出 / 用户输入）和产出。

### 3. 规划异步策略（异步点 = 轮次边界，按这个切 sub_skill）

每个异步 API 在平台运行时都会**切开轮次**：调 exec → `register_async_poll` 注册 → **结束本轮** → 完成时**唤醒** → 新一轮拿结果继续。设计时就把异步点当 sub_skill 的天然分界：

- `callback_enabled=true` 的 API：调用后**结束轮次**等回调。
- 有 `poll_query_api` 的：用 `register_async_poll` 注册，`delay_minutes/poll_interval/max_polls` 按任务量级估（见 `knowledge/CONSTRAINTS.md` 默认区间表），并给出**完成条件** `completion_config`（注册表没配 `success_condition` 时必须显式给）。
- **唤醒后那步必须自包含**：被唤醒时 Agent 只有 poll 结果 + 文件 + SKILL.md，**没有**轮次前的内存变量 → 异步点之后还要用的状态，结束轮次前**落文件**或能从 poll 结果重导出。
- **别写成同步直线**：SKILL.md 显式写「提交 → 注册 → 结束轮次 →【唤醒】→ 读结果 → 继续」。
- 打样阶段用 Runtime Core `wait_result` 验证有授权的 poll API 和完成条件，详见 sub_skill_04。

## 注意事项

- 不要把多个 API 的编排塞进一个脚本——编排是 Agent（SKILL.md）的职责。
- 不要让脚本之间互相 import 业务数据；数据由 Agent 在上下文中传递。
- 源 Skill 的写法被平台约束逼着改时（`threading`/`multiprocessing` 并发、`shutil` 批量文件、环境变量传配置、脚本内 `while`+`sleep` 轮询…），优先按规范改写。改写后可用就不必记差异；确实影响交接时可用 `--kind constraint` 仅记录，但不提报。
- 若 Skill 的 API 与编排合理，却受限于 Agent 的执行能力（例如 Runtime 不支持需要的 Sub Agent、上下文无法传递、异步回调/恢复丢失），不要写成 `missing_capability`。确认它阻塞核心目标且无合理绕过后，用 `--kind agent_runtime --blocking --workaround "无" --report`，由 sub_skill_06 路由到 Agent 能力反馈表单。

## 产出

一份设计蓝图：sub_skill 列表 + 每步的 API/脚本归属 + 数据流 + 异步策略。进入 `sub_skill_04`。
