# 平台 ↔ 本地 执行语义对照（Plugin：Remote MCP + curl + bridge.py）

> Plugin 把线上 Skill 拉到本地跑。跑的是**真实平台 API**，但**跑 Skill 脚本的环境不是平台运行时**。
> 这份文件说明两边哪里一致、哪里不一致——不读它，很容易把「本地失真」当成 Skill 的 bug，
> 或者反过来，把「本地跑通了」当成「平台上也能跑通」。

## 平台上一个 Skill 是怎么跑起来的

```
用户激活 Skill
  └→ 递归展开 linked 子技能 → 每个技能复制到 <session_cwd>/.claude/skills/<name>/（排除 api.json，补 __skill_meta.json）
  │    → 全部 api_codes 进当前会话的 API 白名单
  └→ Agent 读 Skill 的 SKILL.md，按其指引逐步执行；按需才读 sub_skill_NN/SKILL.md
       ├→ 调平台 API：blue_query_api_docs / blue_exec_api        （受白名单 + 额度 + 依赖 + 审批门禁）
       ├→ 跑脚本：run_python_script(script_path, script_args, python_path)
       │    └→ 云沙箱：脚本里的 call_platform_api 经 RPC 交给宿主，宿主做门禁、注入身份、再调用平台
       └→ 等异步：register_async_poll 注册后**结束本轮**，任务完成时**唤醒会话**带回结果
```

**脚本的相对路径基准是工作目录**，技能在 `.claude/skills/<name>/` 下——所以 `script_path` 写
`.claude/skills/<name>/tools/x.py`。

## 当前工作流与准入优先级

Runner/Capability/Builder 都默认分发，按用户意图衔接；日常能力组合不自动进入 Builder。
API 使用以 Runner 主入口的「默认聚焦与远端准入分开」为准：有效 checkout grant 内的垂类/策略 API
仍能进入执行检查，普通声明外 API 的目标为允许补充，未授权受限 API 拒绝。
Agent Service 未配套前仍遵守实际拒绝，不能用脚本、换 mode 或换入口绕过。
本仓不实现权限扩大、会话合并或 Tool Call 入库，也不保证新远端能力已上线。

## 能力映射

| 平台侧 | Plugin 本地等价物 | 一致性 |
|---|---|---|
| 激活 Skill 的落盘结果 | `pull_skill` 返回主 checkout + 递归 `linked[]`，你按 Runner「物化 checkout」用 curl 下载、校验、解压到 `<workspace>/.claude/skills/<name>/` | ✅ 布局、linked 展开、排除 `api.json` / `__skill_meta.json` 一致；依赖缺失时整次失败。**不生成 `CLAUDE.md`**（服务端已退役 `claude_prompt`） |
| Agent 读 SKILL.md / sub_skill 渐进加载 | **你自己**读运行目录下的文件 | 形式一致，**模型不同**（见 F1） |
| `blue_query_api_docs(api_code)` | Remote MCP `blue_query_api_docs` | ✅ 同一注册表、同一返回 |
| `blue_exec_api(api_code, body)` | Remote MCP `blue_exec_api` | ✅ 打真实平台，门禁由服务端执行 |
| `run_python_script(...)` | `python3 scripts/bridge.py`（lease 走 stdin） | ⚠️ 注入语义一致，但**跑在你本机**（ffmpeg / 包 / CPU 都是本机的，F13）；超时不同（F6） |
| 脚本内 `call_platform_api(api_code, body)` | `bridge.py` 注入，父进程经 lease 调 Remote MCP | ✅ **写法、返回结构、失败语义一致，脚本一行不改** |
| 文件上传哨兵 `__call_platform_api_file:` | `bridge.py` 父进程读 workspace 内文件，经 `material_upload_endpoint` 上传 | ✅ 仅支持 `material_upload_proxy.file`，其余 API 的文件字段不支持（F11） |
| `register_async_poll(...)` | `blue_exec_api` 反复调用状态查询 API（见 Runner「3. 处理异步结果」） | ⚠️ 判据一致，**等待方式不同**（F3） |
| 会话工作目录（产物同步回前端） | `.avp_run/<name>/workspace/` | ⚠️ 只在本地，前端看不到（F7） |
| `avp_session_id` | `switch_context(..., mode="skill_runner")` 创建真实会话；id 保持 Remote MCP 私有 | ✅ 真实会话、服务端注入；本地不暴露或伪造 id |
| 人工审批 / 用户交互工具 | Remote MCP 表单 App 回传普通用户消息；需审批的 API 拒绝执行 | ⚠️ 无审批 App，不能用聊天确认放行（F4） |

## 已知失真点

> 本地与平台的下列差异是执行层细节，**默认不向用户披露**（只有阻断时才按 SKILL.md「汇报结果」说）。它们是运行边界，不是默认待办或平台缺陷。只有它确实阻塞当前 Skill 的核心目标、且无法在 Skill 设计中绕过时，才切到 Builder 记录为 `fidelity`；它默认只记录、不提报平台需求。

### F1 · 跑 Skill 的模型不同 → 本地跑通 ≠ 平台跑通

平台交付环境用较小的模型冷读 Skill 并执行；本地是你。你更容易「猜对」SKILL.md 没写清的地方，从而**掩盖 Skill 的指引缺陷**。

**怎么降低失真**：严格按 Skill 自己的指引走，**该按需加载就别预读**所有 sub_skill；遇到「必须靠推测才能继续」的地方，别顺手补上，**记下来**——这正是 Skill 在平台上会翻车的点。

### F2 · 额度 / 依赖 / query-first 由服务端执行，本地不会"放宽"

经 `blue_exec_api` 与 `bridge.py` 的每次调用都过同一套服务端门禁（白名单、`depends_on` 前置依赖、query-first、额度）。
本地没有"告警级"这一档：被拒就是被拒。

**怎么降低失真**：脚本里 `call_platform_api` 返回 `{"error": …}` 时，按错误信息补前置步骤（先 `blue_query_api_docs`、先调依赖 API）；
遇到 `api_not_granted` 是 Skill 的 `api.json` 漏了这个 code，**记下来**，不要靠换入口绕过。

### F3 · 异步等待是当前轮次内轮询，不是平台自动唤醒

平台：`register_async_poll` 注册后**结束本轮对话**，任务完成时唤醒会话，Agent 在新一轮里只拿到 poll 结果与文件。
Plugin：在当前轮次里用 `blue_exec_api` 反复查询状态 API，按完成条件判定成功 / 失败 / 仍在进行；
不会自动续接，所以要给总次数设上限，到上限就如实汇报并由用户决定是否继续，不重提交创建请求。

平台的 `async_event_push_enabled=true` 技能走 Event Bus；Remote MCP 关闭平台事件/回调登记，返回 `wait_result_hint`。
若没有可查询的状态 API，不得假装已拿到结果。

**怎么降低失真**：异步点之后只用查询返回和磁盘文件继续；若必须依赖此前临时上下文，那是 Skill 的恢复设计问题。

### F4 · Remote MCP 没有人工审批通道，需审批的 API 拒绝执行

平台对部分敏感/昂贵操作会走人工审批。Remote MCP 没有审批 App，也不允许绕过这道门禁。

**后果**：需审批的 API 在 Remote MCP 侧被拒绝，不能完成这一步。

**怎么降低失真**：昂贵/不可逆操作仍先征得用户同意；服务端返回需审批而拒绝执行时，停止并如实汇报，不能把普通同意当作平台审批。

### F5 · 脚本静态审查：本地没有，平台有

平台对云沙箱里的 Python 脚本有静态策略与护栏；本地 `bridge.py` **不做静态审查**，只做凭据隔离。
所以一个能在本地跑通的脚本，不等于平台会放行它。

**怎么降低失真**：把本地通过当作"逻辑正确"的证据，不当作"平台合规"的证据；Builder 的 `skill validate` 类检查若本制品不提供，
就如实说明没有做平台侧静态校验。

### F6 · 单脚本超时不同

平台沙箱有自己的默认执行超时，Agent 还能显式传 `timeout` 覆盖。`bridge.py` 默认 `--timeout 3600` 秒。

**怎么降低失真**：本地耗时只说明「这段逻辑要跑这么多活」，**不能**换算成平台耗时（见 F13）。
真正要记的是：这个脚本在平台上是否需要显式抬 `timeout`，或者拆分 / 改异步。

### F7 · 工作目录不与平台会话空间同步

平台脚本的 cwd 是会话工作目录，产物会同步进前端会话空间，用户能看见、后续轮次能读到。本地产物只落在 `.avp_run/<name>/workspace/`。

**后果**：涉及「把文件给用户看」「跨轮次读同一份文件」的步骤，本地只能验到「文件写出来了」。要让用户看到，
通过 `material_upload_proxy` 上传后用素材 CDN 链接交付。

### F8 · 运行时注入字段：服务端注入，本地拿不到的拿不到

平台从会话上下文注入 `user_uid` / `project_id` / `avp_session_id` 等。经 Remote MCP 调用时，这些由服务端按当前 Context 注入，
**脚本无法伪造，你也不要自己编**。

**其余注入字段拿不到**：平台运行时才有的值（上一轮产物引用等）本地没有等价来源，报 `Field required` 时**这是预期限制，不是参数错误**——
别反复试、别瞎填。标注「运行时注入字段，平台侧验证」，跳过或换等价 API 继续。

> **永远不要自己编一个 `avp_session_id` 字符串糊过校验**：编了可能过，但会往平台留痕里写一条指向不存在会话的脏数据。

### F9 · 非属主且未开放下载的 Skill

`pull_skill` 的可见范围是「目录可见 = 可拉取」（自己的 Skill、他人已发布的全局 Skill、同团队他人已发布的 Skill），**不看 `derivable`**。
所以 Web 的"禁止下载"开关对本制品不生效；拉不到就是不可见或版本不可拉，按服务端返回的错误如实说明，不换入口。

### F10 · 身份与项目来自当前 Context

平台由宿主闭包注入 `user_uid` / `project_id`。Plugin 里它们来自当前 `skill_runner` Context——语义等价，但**项目是你当前绑定的那个**。
跑之前用 `get_current_context` 确认团队 / 项目就是用户想操作的那个，别把测试数据写进别人的工程。换工作区必须先问用户。

### F11 · 文件上传（`__call_platform_api_file:` 哨兵）只支持素材上传

平台：脚本写 `{"file": "__call_platform_api_file:assets/a.mp4"}`，**宿主**读出文件转成 multipart 发给后端。
Plugin：`bridge.py` 的父进程在本机读 workspace 内的文件，经 `material_upload_endpoint` 上传，因此：

- **只支持** `material_upload_proxy` 的 `file` 字段，且一次一个文件；
- 文件必须在 workspace 内、是普通文件（不是软链）、非空、不超过 500 MiB；
- 其他 API 的文件字段、嵌套在数组里的哨兵，都会被直接拒绝，不会发出任何请求。

**绕行办法（择一）**：① 换 URL 导入类 API（`material_url_add` / `material_image_add`）；② 先把文件经 `material_upload_proxy` 上传，
之后只用 `material_id`。

### F12 · 脚本里 API 失败是「返回值」不是「异常」——两边都是

这条不是失真，是**容易写错的对齐点**：平台侧 `call_platform_api` 在 API 报错 / 白名单拦截 / 审批拒绝时，都是**返回** `{"error": "…"}` 给脚本，
只有宿主通道真挂了才抛异常。`bridge.py` 与之一致。

**后果**：脚本里 `res = call_platform_api(...)` 之后那句 `if res.get("error")` 是**会走到**的分支，本地能验；
而 `try/except` 包住 call 却不检查返回值的脚本，在两边都会把失败当成功往下走——看到这种写法就是 Skill 的真问题，记下来。

**一个本地特有的补充**：`bridge.py` 在平台调用"结果未知"或 lease 失效时，即使脚本自己捕获了异常并正常退出，
也会把整次运行标记为失败（`success:false`，退出码 6 或 7）。这是有意的：吞掉这类失败会让你把一个可能已经执行的写操作当成没发生。

### F13 · 脚本的运行环境是**你本机**，不是平台沙箱

`bridge.py` 起的是你机器上的一个子进程（cwd = workspace）。只有 `call_platform_api` 走 HTTP 出去，除此之外**一切都在本机**：

| 东西 | 本地执行 | 平台（云沙箱） |
|---|---|---|
| 文件、产物 | 你本机 `.avp_run/<name>/workspace/` | 沙箱工作目录，且**同步回前端会话空间**（见 F7） |
| `ffmpeg` 及其他二进制 | **你本机装的那个版本**（没装就直接跑不了） | 镜像预装（ffmpeg / jq / git / node） |
| Python 第三方包 | 你本机 env 里有什么算什么 | 镜像固定那批（requests / pillow / pandas / numpy / lxml / openpyxl / PyYAML / httpx / aiohttp / bs4 / pydantic / python-dotenv） |
| CPU / 内存 | 你本机 | 技能级配置（不同沙箱类型规格不同） |

**三个方向的坑，都要当差异记**：

1. **本机缺东西 → 本地假失败**：没装 ffmpeg、缺 codec、缺某个 pip 包 → 本地跑不过，但平台完全正常。别据此改 Skill。
2. **本机多东西 → 本地假成功**：脚本 import 了你本机装过、镜像里没有的包 → 本地过、平台 `ModuleNotFoundError`。
   跑通之后**核一遍脚本的 import 清单**是否都在上表那批里。
3. **耗时不可换算**：转码/渲染快慢取决于你的机器。本地 300s 不代表平台超时，本地 30s 也不代表平台够快。

另外，`bridge.py` 只隔离**凭据**，不隔离文件系统：脚本仍能读写你本机的文件。对来源不明的 Skill 要像对待任何本地脚本一样谨慎。

## 结论怎么下

跑完一个 Skill，向用户交代三件事，别混在一起说：

1. **业务上跑出了什么**：真实产物路径、关键 API 返回。
2. **哪些步骤没能在本地完整验证**：命中了上面哪些失真点（F1~F11、F13）。
3. **发现的 Skill 真问题**：`api.json` 漏 code、唤醒后不自包含、SKILL.md 指引不清、脚本超时、`call_platform_api` 返回值不检查（F12）——这些与失真点不同，**是 Skill 该改的地方**，值得回到转化模式修。
