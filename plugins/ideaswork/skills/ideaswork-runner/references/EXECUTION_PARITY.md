# 平台 ↔ 本地 执行语义对照（执行模式必读）

> 执行模式把线上 skill 拉到本地跑。跑的是**真实平台 API**，但**跑 skill 的环境不是平台运行时**。
> 这份文件说明两边哪里一致、哪里不一致——不读它，很容易把「本地失真」当成 skill 的 bug，
> 或者反过来，把「本地跑通了」当成「平台上也能跑通」。

## 平台上一个 skill 是怎么跑起来的

```
用户激活 skill（slash / activate_skill）
  └→ SkillService.activate()：递归展开 linked 子技能 → 每个技能复制到
  │    <session_cwd>/.claude/skills/<name>/（排除 api.json，补 __skill_meta.json）
  │    → claude_prompt 写进 <session_cwd>/CLAUDE.md 托管块
  │    → 全部 api_codes 进 tracker 白名单
  └→ Agent 读 skill 的 SKILL.md，按其指引逐步执行；按需才读 sub_skill_NN/SKILL.md
       ├→ 调平台 API：blue_query_api_docs / blue_exec_api        （受白名单 + 额度 + 依赖 + HITL 门禁）
       ├→ 跑脚本：run_python_script(script_path, script_args, python_path)
       │    └→ 沙箱：安全审查 → 注入 preamble（builtins.call_platform_api / chdir / sys.argv / __file__）
       │         └→ 脚本里的 call_platform_api 经**文件 RPC** 交给宿主
       │              宿主：resolve_file_refs 解析文件哨兵 → check_api_access 门禁
       │                    → 注入身份 → HITL → blue_exec_api → 心影后端
       └→ 等异步：register_async_poll 注册后**结束本轮**，任务完成时**唤醒会话**带回结果
```

**脚本的相对路径基准是 `session_cwd`**，技能在 `.claude/skills/<name>/` 下——
所以平台 SKILL.md 里的 `script_path` 写 `.claude/skills/<name>/tools/x.py`。
`agent_skills/<name>/` 是**设计期的源目录**，运行工作目录里没有它（照抄会跑到错目录）。

本地执行模式把上面每一环都换成了等价物。`pull` 复刻了激活的四件落盘事（linked 展开、
`.claude/skills/` 布局、CLAUDE.md 托管块、api 白名单），`run` 复刻了沙箱 preamble 与
`call_platform_api` 的可见行为——**其余仍有偏差**。

## 当前工作流与准入优先级

Runner/Capability/Builder 都默认分发，按用户意图衔接；日常能力组合不自动进入 Builder。
API 使用以 Runner 主入口的「默认聚焦与远端准入分开」为准：有效 checkout grant 内的垂类/策略 API
仍能进入执行检查，普通声明外 API 的目标为允许补充，未授权受限 API 拒绝。
下文硬 grant 描述反映旧服务端行为；Agent Service 未配套前仍遵守实际拒绝，不能用 CLI/脚本/mode 绕过。
本仓不实现权限扩大、会话合并或 Tool Call 入库，也不保证新远端能力已上线。

## 新 Runtime Core 架构（2026-09-18）

以下是新 Codex target 的唯一映射，优先级高于本文后续旧 `avp_local`/`local_rpc` 描述；后续旧段落只保留
为 legacy 制品的差异参考，**不得作为新 Codex Plugin 或新 CLI 的操作指引**。

| 平台原语 | 新架构入口 |
|---|---|
| `blue_query_api_docs` / `blue_exec_api` / batch | Remote MCP |
| `run_python_script` | `ideaswork runtime python` |
| 脚本内 `call_platform_api` | Runtime Core Unix socket bridge -> Remote MCP |
| `sandbox_bash` | Host Bash |
| `register_async_poll` | `ideaswork runtime wait-result` |
| `ask_user_interact`（含素材字段） | Remote MCP App；需要审批的 API 在 Remote MCP 侧拒绝执行 |

独立 CLI 使用标准 OAuth session；Codex Plugin Runtime 不读取该 session。Plugin 的 lease 随 Remote MCP `pull_skill` 返回自动下发（短 TTL、Context 绑定），并在 lease 有效期间复用；仅失效、额度耗尽或 Context 变化后才通过 `create_runtime_lease` 重签。随后 Runtime Core 调用 Runtime lease endpoint。新 Runner 不使用旧 `ideaswork skill run`、`exec-api`、`poll`、`session` 或 Agent Service `local_rpc`。

## 能力映射

> 平台原语（docs / exec / run / poll）**优先走 `ideaswork` MCP 工具**——session 绑定与异步
> 回流只挂在 MCP 调用上（见 SKILL.md §2「MCP 优先」）。下表 CLI 命令是 MCP 不可用时的
> 降级等价物，降级须在结论中列出。

| 平台侧 | 本地等价物 | 一致性 |
|---|---|---|
| `SkillService.activate()` 的落盘结果 | Remote MCP `pull_skill` 返回主 checkout + 递归 `linked[]`，Runtime Core `checkout --linked-json` → `workspace/.claude/skills/<name>/` + `CLAUDE.md` | ✅ 布局/排除 api.json/`__skill_meta.json`/linked 展开一致；依赖缺失时整次失败 |
| Agent 读 SKILL.md / sub_skill 渐进加载 | **你自己**（Claude Code）读运行目录下的文件 | 形式一致，**模型不同**（见失真 F1） |
| `blue_query_api_docs(api_code)` | Remote MCP `blue_query_api_docs` | ✅ 同一注册表、同一返回 |
| `blue_exec_api(api_code, body)` | Remote MCP `blue_exec_api` | ✅ 打真实平台；⚠️ 门禁不同（F2） |
| `run_python_script(...)` | `ideaswork runtime python` | ⚠️ preamble 语义复刻，但**跑在你本机**（ffmpeg / 包 / CPU 都是本机的，F13）；审查与超时也不同（F5/F6） |
| 脚本内 `call_platform_api(api_code, body)` | Runtime Core 通过 Unix socket bridge 注入，再由父进程调用 Remote MCP | ✅ **写法、返回结构、失败语义一致，脚本一行不改** |
| API 执行声明与 checkout grant | `pull_skill` 保留主 Skill 与 linked checkouts 的声明和受限授权；声明外普通 API 依远端准入补充 | 旧部署仍硬拦全部声明外调用；目标策略由 Agent Service 配套，不能本地放开 |
| `resolve_file_refs`（文件上传哨兵） | 本地预检 + 明确报错 | ❌ **远端服务读不到本机文件**（F11） |
| `register_async_poll(...)` | 统一用一次 `ideaswork runtime wait-result --tasks-json ...` 串行等待整批任务 | ⚠️ 判据一致，**等待方式不同**（F3） |
| 会话工作目录（产物同步回前端） | `.avp_run/<name>/workspace/` | ⚠️ 只在本地，前端看不到（F7） |
| 会话上下文注入的 `avp_session_id` | `switch_context(..., mode="skill_runner")` 创建真实会话；id 保持 Remote MCP 私有 | ✅ 真实会话、服务端注入；本地不暴露或伪造 id |
| HITL 人工审批 / 用户交互工具 | Remote MCP 表单 App 回传普通用户消息；需审批的 API 拒绝执行 | ⚠️ 无审批 App，不能用聊天确认或旧 local RPC 放行替代 |


## 已知失真点

> 本地与平台的下列差异是运行边界，不是默认待办或平台缺陷。只有它确实阻塞当前 Skill 的核心目标、且无法在 Skill 设计中绕过时，才切到 Builder 记录为 `fidelity`；它默认只记录、不提报平台需求。

### F1 · 跑 skill 的模型不同 → 本地跑通 ≠ 平台跑通

平台交付环境用较小的模型冷读 skill 并执行；本地是你。你更容易「猜对」SKILL.md 没写清的地方，从而**掩盖 skill 的指引缺陷**。

**怎么降低失真**：严格按 skill 自己的指引走，**该按需加载就别预读**所有 sub_skill；遇到「必须靠推测才能继续」的地方，别顺手补上，**记下来**——这正是 skill 在平台上会翻车的点。真要验「陌生 agent 能否被导对路」，还是得用平台的 `?validate=1&skill=<name>` 冷跑。

### F2 · api.json 白名单在本地是「告警级」，额度 / 依赖 / query-first 门禁完全没有

平台侧对 skill 的 API 调用有一整套门禁（`check_api_access`：白名单、调用次数上限、
`depends_on` 前置依赖、部分 API 要求先 `blue_query_api_docs`）。本地打样 RPC 为设计用途
**权限全开**（wildcard tracker），门禁只能在本地补一部分：

| 门禁 | 平台 | 本地 |
|---|---|---|
| api.json 白名单 | 硬拦 | `ideaswork skill run` 注入白名单，**默认告警**、`--strict` 才拦 |
| 调用次数上限（per session / per turn） | 硬拦 | 无 |
| `depends_on` 前置依赖 | 硬拦 | 无 |
| query-first（未 querydocs 就 exec） | 视 `skip_query_first` 硬拦 | 无 |

`ideaswork skill exec-api` 是你手动调，**不过白名单**（对齐平台 Agent 直接用 blue_exec_api 时
仍受门禁这点，本地做不到）。

**怎么降低失真**：`ideaswork skill brief <name>` 先看白名单和 `skip_query_first`；跑脚本时看到
「不在白名单里」的告警**别忽略**——那是 skill 的真问题（api.json 漏了这个 code），记下来。
拿不准时用 `--strict` 跑一遍，让门禁真拦。

### F3 · 异步等待是当前调用内轮询，不是平台自动唤醒

平台：`register_async_poll` 注册后**结束本轮对话**，任务完成时唤醒会话，Agent 在新一轮里只拿到
poll 结果与文件。Codex Plugin：Runner 使用 Runtime Core `wait_result` 在当前调用里查询原
`query_api_code`，按完成条件返回 `succeeded` / `failed` / `timeout`；不需要顶层 Adapter，
也不会自动续接。超过单次等待或 lease 有效期时分段处理，不能因超时重提创建请求。

平台的 `async_event_push_enabled=true` 技能走 Event Bus，返回 `event_wait_registered=true`
时不再注册轮询。Remote MCP 关闭平台事件/回调登记并返回 `wait_result_hint`；Plugin 统一使用本地
`wait_result` 查询最终结果。若没有可查询的状态 API，不得假装已拿到结果。

**怎么降低失真**：异步点之后只用 poll 返回和磁盘文件继续；若必须依赖此前临时上下文，
那是 Skill 的恢复设计问题。

### F4 · Remote MCP 没有 HITL 人工审批通道，需审批的 API 拒绝执行

平台对部分敏感/昂贵操作会走人工审批。新 Remote MCP 没有审批 App，也不允许绕过这道门禁。

**后果**：需审批的 API 在 Remote MCP 侧被拒绝，不能完成这一步；独立 CLI 登录态也不能当作 Plugin 的审批凭证。

**怎么降低失真**：昂贵/不可逆操作仍先征得用户同意；若服务端返回需审批而拒绝执行，停止并如实汇报，不能将普通同意当作平台审批。

### F5 · 脚本静态审查：**本地比平台生产环境更严**（方向别搞反）

平台的 Python 脚本静态策略按**沙箱后端分档**（`guardrails/security_policy.py`）：

| 后端 | 静态黑名单 | LLM 语义审查 |
|---|---|---|
| `vefaas` / `e2b`（**生产在用**；`VeFaaSSandboxProvider(E2BSandboxProvider)`） | 只有 `ctypes` / `signal`（`SANDBOX_CODE_BLOCKED_PATTERNS` 是空的） | **不跑**（`SANDBOX_CODE_ENABLE_LLM_GREYLIST=False`） |
| `local`（宿主裸跑） | `subprocess` / `threading` / `multiprocessing` / `concurrent` / `shutil` / `importlib` / `socket` / `os.system` … | 跑（含灰名单：exec/eval、动态路径、base64+exec…） |

**所以 `subprocess`、`ffmpeg`、`ThreadPoolExecutor` 在生产沙箱里是允许的**——线上
material-cli 的 `--batch-upload-files` 就在用 `ThreadPoolExecutor`。

`ideaswork skill run` 据此分两档报：
- 命中 `ctypes`/`signal` → 默认**拒绝执行**（平台会先让 LLM 复核，多半仍拒），`--force` 强跑；
- 命中「宿主裸跑档 + 薄脚本设计规范」项 → 只提示一句，`--strict` 才拦。第二档命中
  **不等于平台会拦**，但转化模式的 `ideaswork skill validate` 仍按设计规范判 FAIL（薄脚本不该开线程、
  不该用 `os.environ` 传配置），那是设计约束而非运行时门禁。

### F6 · 单脚本超时不同

平台沙箱默认 `SandboxConfig.timeout`（代码里 120，released `conf/config.conf` 给的是 **240**），
Agent 还能给 `run_python_script` 显式传 `timeout` 覆盖（工具描述建议长任务 300–2700）。
`ideaswork skill run` 默认 900s（`--timeout 0` 不限制），超过 240s 会提示一句。

**怎么降低失真**：本地耗时只说明「这段逻辑要跑这么多活」，**不能**换算成平台耗时（见 F13）。
真正要记的是：这个脚本在平台上是否需要显式抬 `timeout`，或者拆分/改异步。

### F7 · 工作目录不与平台会话空间同步

平台脚本的 cwd 是会话工作目录，产物会同步进前端会话空间，用户能看见、后续轮次能读到。本地产物只落在 `.avp_run/<name>/workspace/`。

**后果**：涉及「把文件给用户看」「跨轮次读同一份文件」的步骤，本地只能验到「文件写出来了」。

### F8 · 运行时注入字段：会话已能真建，其余仍拿不到

平台上 skill 永远是**在某个会话里**被激活执行的，`avp_session_id` 由运行时从会话上下文注入脚本参数。不少 skill 拿它做**付费留痕强约束**（如 xy-aigc-cli-v1：每条付费创建都要求非空 `avp_session_id`，缺了就拒绝产生 event）。

**`avp_session_id` 已解决**：`ideaswork skill pull` 会顺带在平台真建一个会话（Engine `POST /api/avp_agent/session/create`），缓存进 `.avp_run/<name>/_session.json`；`run` / `exec-api` 自动把参数里的 `<avp_session_id>` / `<project_id>` 占位符替成真值——对齐平台的运行时注入。手工看/换/删用 `ideaswork skill session <name> [--new|--delete]`。

**但这个会话是合成的**，与平台语义仍有差：它由 skillrun 新建，**没有对话历史、前端没人在看**，`session_biz_type` 取 Engine 默认。所以「跨轮次读同一会话的上下文」「产物在前端会话空间可见」这类行为验不到（另见 F7）。

**其余注入字段仍然拿不到**：平台从会话上下文注入的其他值（运行时才有的 sub_id、上一轮产物引用等）本地没有等价来源，报 `Field required` 时**这是预期限制，不是参数错误**——别反复试、别瞎填。标注「运行时注入字段，平台侧验证」，跳过或换等价 API 继续。

> **永远不要自己编一个 `avp_session_id` 字符串糊过校验**：CLI 只查非空，编了能过，但会往平台留痕里写一条指向不存在会话的脏数据。拿不到就用 `ideaswork skill session` 真建一个。

### F9 · 非属主且未开放下载的 skill 只能拉到文本文件

`/export` 的下载门禁是 **属主恒可 + 他人须作者打开 `derivable`（且已发布、同团队或全局）**。
被拒时（「无权下载该技能」）`pull_skill` 自动改走逐文件 `/file/read`——但**二进制资产
（音频、图片、字体）读不到内容**，会列在返回的 `skipped_binary` 里。`ideaswork skill list`
的 `DL` 列提前告诉你这个技能能不能整包下。

**后果**：依赖内置资产（如 BGM、水印图）的步骤在本地跑不完整。用自己的等价素材替代，并在结论里说明「该步用替代素材验证」。

### F10 · 身份与上下文来自本地配置

平台由宿主闭包注入 `user_uid` / `project_id`，脚本无法伪造。本地由 `local_rpc` 会话按你的 `ideaswork` 登录态 / `config.json` 注入——语义等价，但**project 是你本地选的那个**。跑之前确认 `avp_env.py` 里的 `project_id` 就是你想操作的项目，别把测试数据写进别人的工程。

`team_id` 同理：`ideaswork skill list` / `pull` 都带上了当前团队，**换团队看别的技能要
`ideaswork team use <team_id>`**，不是在命令上加参数。`--personal` 可以按「个人空间」
列（`team_id=""`，只剩全局技能），用来验证「这个技能在没有团队上下文时还看得见吗」。

### F11 · 文件上传（`__call_platform_api_file:` 哨兵）本地跑不通

平台：脚本写 `{"file": "__call_platform_api_file:assets/a.mp4"}`，**宿主**（与沙箱共享
session 工作目录）读出文件转成 multipart 发给后端（`resolve_file_refs`）。
本地：这个「宿主」是**远端 agent_service**，读不到你机器上的文件。

`call_platform_api` 会在本地先检查：文件不在工作目录里 → 直接报路径问题；文件在但服务是
远端 → 返回一条讲清原因的 `{"error": …}`，**不会**让你收到服务端 500。

**绕行办法（择一）**：① 换 URL 导入类 API（`material_url_add` / `material_image_add`）；
② 先在平台把素材上传好，本地只用 `material_id`；③ 自己起一份本地 agent_service，
`AVP_LOCAL_ENDPOINT=http://127.0.0.1:<port>`（或设 `AVP_LOCAL_SERVER_SHARES_FS=1`）——
此时哨兵会原样透传给服务端解析，行为与平台一致。

**这属于本地失真，不是 skill 的 bug**，别改 skill 去绕它。

### F12 · 脚本里 API 失败是「返回值」不是「异常」——两边都是

这条不是失真，是**容易写错的对齐点**，写在这里防止误判：平台侧 `call_platform_api` 在
API 报错 / 白名单拦截 / HITL 拒绝时，都是**返回** `{"error": "…"}` 给脚本（RPC 层视为成功），
只有宿主 RPC 真挂了才抛异常。本地 runtime 与之一致。

**后果**：脚本里 `res = call_platform_api(...)` 之后那句 `if res.get("error")` 是**会走到**的
分支，本地能验；而 `try/except` 包住 call 却不检查返回值的脚本，在两边都会把失败当成功往下走
——看到这种写法就是 skill 的真问题，记下来。

### F13 · 脚本的运行环境是**你本机**，不是平台沙箱

`ideaswork skill run` 起的是你机器上的一个子进程（`sys.executable`，cwd = 该 skill 的
`workspace/`）。只有 `call_platform_api` / `exec-api` / `docs` / `poll` 走 HTTP 出去。
除此之外**一切都在本机**：

| 东西 | 本地执行模式 | 平台（`backend=vefaas`） |
|---|---|---|
| 文件、产物 | 你本机 `.avp_run/<name>/workspace/` | 沙箱工作目录，且**同步回前端会话空间**（见 F7） |
| `ffmpeg` 及其他二进制 | **你本机装的那个版本**（没装就直接跑不了） | 镜像预装（`sandbox_template/e2b.Dockerfile`：ffmpeg / jq / git / node20） |
| Python 第三方包 | 你本机 env 里有什么算什么 | 镜像固定那批（requests / pillow / pandas / numpy / lxml / openpyxl / PyYAML / httpx / aiohttp / bs4 / pydantic / python-dotenv） |
| CPU / 内存 | 你本机 | 技能级配置：`default` 0.5~2 vCPU、`ffmpeg` 类型 2~8 vCPU + 4~16 GiB（`SANDBOX_TYPE_SPECS`；`brief` 会打出该技能配的是哪档） |

**三个方向的坑，都要当差异记**：

1. **本机缺东西 → 本地假失败**：没装 ffmpeg、缺 codec、缺某个 pip 包 → 本地跑不过，
   但平台完全正常。别据此改 skill。
2. **本机多东西 → 本地假成功**：脚本 import 了你本机装过、镜像里没有的包 →
   本地过、平台 `ModuleNotFoundError`。跑通之后**核一遍脚本的 import 清单**是否都在上表那批里。
3. **耗时不可换算**：转码/渲染快慢取决于你的机器。本地 300s 不代表平台超时，本地 30s 也不代表
   平台够快——尤其技能配了 `ffmpeg` 沙箱（8 vCPU）而你在笔记本上跑时，两边差一个数量级。

顺带一句：这也正是 F11 文件上传跑不通的根因——文件在**你本机**，而按平台语义该读这个文件的
「宿主」在远端。

## 结论怎么下

跑完一个 skill，向用户交代三件事，别混在一起说：

1. **业务上跑出了什么**：真实产物路径、关键 API 返回。
2. **哪些步骤没能在本地完整验证**：命中了上面哪些失真点（F1~F11、F13）。
3. **发现的 skill 真问题**：`api.json` 漏 code、唤醒后不自包含、SKILL.md 指引不清、脚本超时/命中平台禁用项、`call_platform_api` 返回值不检查（F12）——这些与失真点不同，**是 skill 该改的地方**，值得回到转化模式修。
