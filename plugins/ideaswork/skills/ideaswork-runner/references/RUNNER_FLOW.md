# Codex Plugin Runner 主链路

本图描述已发布 Skill 在 **Codex Plugin + Remote MCP + 本地 Runtime Core** 中的运行流程；
独立终端 CLI 的 `ideaswork skill pull` 是另一条入口，见 [CLI_BINDING.md](CLI_BINDING.md)。图中的 `checkout` 指用
`checkout_id` 下载并物化 ZIP，不是 Git checkout，也不是 SHA-256 校验。

```mermaid
flowchart TD
    A["用户要运行已发布 Skill"] --> B{"IdeasWork Remote MCP<br/>已连接？"}
    B -- 否 --> B0["用户完成 Connect IdeasWork / OAuth<br/>本轮停止，连接后继续"]
    B -- 是 --> C{"已有明确的 skill_id？"}

    C -- 否 --> C1["browse_skills() 一次<br/>在 Catalog 内搜索、翻页、选择"]
    C1 --> C2["等待用户选择<br/>下一轮取得 skill_id"]
    C -- 是 --> D["get_current_context()"]
    C2 --> D

    D --> E{"用户明确要切换团队或项目？"}
    E -- 是 --> E1["browse_contexts()<br/>用户通过表单选择 context_ref"]
    E1 --> E2["用户消息 interaction_response 确认后<br/>switch_context(skill_runner)"]
    E -- 否 --> F{"无有效 Context、模式不符<br/>或明确要求新会话？"}
    F -- 是 --> F1["switch_context(skill_runner)<br/>省略 context_ref，使用当前/OAuth 默认工作区<br/>初始化或仅切 mode 不弹工作区表单"]
    F -- 否 --> F2["复用当前 Context"]

    E2 --> G["pull_skill(skill_id)<br/>取得 checkout_id 和 runtime lease"]
    F1 -- 绑定成功 --> G
    F1 -- 服务端明确要求选择工作区 --> E1
    F2 --> G

    G --> H{"linked 数组有效<br/>且未缺少已知必需依赖？"}
    H -- 否 --> I["核对已知依赖身份<br/>先复用 checkout 或在同一 Context 补拉"]
    I --> IR{"恢复成功？"}
    IR -- 否 --> IF["停止受影响阶段<br/>报告缺失技能和实际失败原因"]
    IR -- 是 --> J2
    H -- 是，包括合法空数组 --> J1["一次 Runtime Core checkout --linked-json<br/>通过 lease 下载并校验主包和完整依赖图"]
    J1 --> J2["主 Skill 写入 skill/<br/>子技能写入 linked/子Skill<br/>及同一 workspace/.claude/skills/"]
    J2 --> K["Host 整理受管 CLAUDE.md<br/>API 清单"]

    K --> L["先读 CLAUDE.md，再读主 SKILL.md<br/>子技能只在对应阶段加载"]
    L --> M{"原 Skill 的下一步"}

    M -- 必需子技能未下发或未物化 --> MR["按 LINKED_RECOVERY 核实并尝试补拉<br/>成功后继续原阶段"]
    MR -- 成功 --> M
    MR -- 失败 --> IF
    M -- 用户输入或素材 --> U["ask_user_interact 表单（内嵌素材字段）<br/>等待用户消息 interaction_response"]
    U --> M
    U -- App 内取数不支持 --> UF["material_pick_request → browse_materials 取数<br/>用户文字确认后用 draft 回填表单"]
    UF --> U

    M -- 平台 API --> P["先查询目标 API 文档<br/>blue_exec_api / blue_exec_batch"]
    P --> Q{"需要用户审批？"}
    Q -- 否 --> M
    Q -- 是 --> Z["Remote MCP 拒绝执行<br/>说明限制，不绕过审批"]
    M -- 已完成 --> Z0["汇报产物、限制与问题"]

    M -- Python 脚本 --> PY["exec_python：本机子进程<br/>通过 bridge 调平台 API"]
    PY --> M
    M -- Bash --> SH["Host Bash：在 Skill workspace 执行"]
    SH --> M

    M -- 异步任务 --> W["wait_result：按状态 API 本地轮询"]
    W --> WS{"查询结果"}
    WS -- 成功 --> M
    WS -- 超时 --> W1["保留任务 ID；决定是否分段续等<br/>不重新创建任务"]
    W1 --> W
    WS -- 明确失败 --> Z0
```

- 主 Skill 的 `checkout` 写入 `.avp_run/<主Skill名>/skill/` 和
  `.avp_run/<主Skill名>/workspace/.claude/skills/<主Skill名>/`。
  linked 子技能通过 `--primary-skill-name <主Skill名>` 共享这个 workspace，
  写入 `.avp_run/<主Skill名>/linked/<子技能名>/` 和同一 workspace 下的
  `.claude/skills/<子技能名>/`；不创建子技能自己的 `.avp_run` 目录。
- 只有需要发现 Skill 时才调用 Catalog。初始化或仅切 mode 不弹工作区表单；只有用户明确换工作区，
  或服务端确认默认工作区不可用时才查询候选并让用户选择。原 Context 丢失时恢复原工作区，不静默改用默认项目。
  仅在 Context 初始化、模式不符或明确切换等条件下调用 `switch_context`；
  `pull_skill` 已提供 lease，只有失效、额度耗尽或 Context 变化才重签。
- linked 子技能、用户交互、审批拒绝、脚本及异步等待均为按需分支。Runtime Core 的
  lease 恢复只重试尚未完成的步骤；Python 脚本可能已产生副作用，须先核对状态，不能盲目重跑。
- checkout 负责归档落盘；受管 `CLAUDE.md`、linked prompt 与 API 清单的整理仍是后续
  Host 步骤，不能把它误认为第二次下载。

- 缺失的必需子技能先按 [LINKED_RECOVERY.md](LINKED_RECOVERY.md) 核实并尝试补拉；
  只有恢复失败才停止受影响阶段并报告实际原因。已随主 pull 下发的 checkout 不重复 pull。
