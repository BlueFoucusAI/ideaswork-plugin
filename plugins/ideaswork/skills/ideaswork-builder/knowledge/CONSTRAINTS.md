# 平台约束速查（本地打样必读）

> 本地打样时按这份约束写脚本。脚本本地与平台是同一份代码：`call_platform_api` 由运行时注入，无需桥接块。
> 完整规范见平台 `agent_skills/avp_skill_creator/knowledge/skill_spec.md`。

## 发现 API 的优先级（打样优先通用能力）

设计期在 `sub_skill_02` 发现 API 时遵守：

- **优先平台通用能力**：`AI_INFRA/*`（生图/视频/TTS/LLM/ASR/MODEL）、`PLATFORM_INFRA/*`（项目/工程/分镜/素材/任务）、`UTILS/*`（翻译/语言）。
- **遵守实际远端准入**：`blue_list_apis` 是当前可用范围，不是全量注册表；Builder 保留现有授权机制，不自动继承受限 API grant。普通能力按需使用 capability 路径，旧部署拒绝时不绕过。
- **垂类/策略能力按需且获授权使用**：垂类以服务端 DB category 的 `VERTICAL` 前缀判定，策略按服务端特殊标识判定，不猜 code 名称。有效 Skill grant 内的受限 API 可正常使用；本地 api.json 和历史成功不授予权限。外部直连不能靠旧 `local_rpc` 补充。

## 核心原则：API-First

业务编排（调哪些 API、按什么顺序、依赖关系）由 **Agent** 负责，脚本只做**纯计算**（LLM 文本生成、TTS 合成等）。

| 操作 | 正确做法 | 禁止 |
|------|----------|------|
| 调平台业务 API | Agent 直接 `blue_exec_api` / 脚本内 `call_platform_api()` | 在脚本里堆编排逻辑 |
| 等待异步任务 | Skill 指令声明轮询；Plugin 本地用 Runtime Core `wait_result` | 脚本内 `while` + `sleep` 死等 |
| LLM / TTS | 薄脚本：加载 prompt → 调用 → 写结果文件 | — |

### 异步任务的 register_async_poll 参数（给个有依据的起点）

对 `callback_enabled=true` 的 API：调用后直接结束轮次等回调，**不注册轮询**。
对只有 `poll_query_api`（无回调）的 API：用 `register_async_poll`，参数按**任务类型量级**估，别拍脑袋：

| 任务类型 | delay_minutes（首次查询前等待） | poll_interval（秒） | max_polls |
|---|---|---|---|
| 文本/分镜/脚本类 LLM 生成 | 0~1 | 20~30 | 10~20 |
| 图片生成 | 1 | 30 | 20 |
| 单条语音 TTS | 0 | 15~20 | 10 |
| 视频渲染 / 成片导出（打样阶段**不要真跑**） | 2~5 | 60 | 30~60 |

> 原则：`delay_minutes + poll_interval × max_polls` 要 ≥ 该任务最坏耗时，留足余量但别无脑拉大（占用轮询额度）。**草稿里注明这些值是按量级估的、上线前用真实任务耗时校准**。

## 沙箱禁忌（平台会拦截，本地也别用）

| 禁止项 | 被拦截关键字 | 替代方案 |
|--------|--------------|----------|
| 动态导入 | `importlib`、`__import__(` | `python_path` 参数 + 普通 `from xxx import yyy` |
| 多线程/多进程 | `threading`、`multiprocessing`、`concurrent` | 单线程顺序，或拆多脚本由 Agent 编排 |
| 批量文件操作 | `shutil` | 逐文件 `open()` / `os.rename()` |
| 网络服务 | `socket`、`http.server` | `call_platform_api()` |
| 路径穿越 | 字符串含 `..`、`~`、`/etc/`、`/proc/` | `__file__` 或当前工作目录相对路径 |

> **进程派生已放开**：`subprocess`（及 `os.system`/`os.popen`）不再拦截——平台沙箱**自带 `ffmpeg`/`ffprobe`**（在 PATH 上）。脚本可直接 `subprocess.run(["ffmpeg", ...])` 做视频探测/抽帧/转码/音频分析等 ffmpeg 能干的纯计算，属薄脚本合法用法（业务 API 仍走 `call_platform_api`）。注意：进程派生仅用于 ffmpeg 这类本地媒体处理，别用它绕过平台 API 去跑别的服务。

## 传参规范（硬性）

- **禁止用环境变量传配置**：`os.environ` / `os.getenv` 在平台多会话共享进程，会污染其他会话。
- 所有运行时配置（模型名、max_tokens、超时、密钥…）一律通过**命令行参数**传入，脚本内用 `argparse` 接收。

```python
# ✅ 正确
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--input", required=True)
args = parser.parse_args()

# ❌ 错误
model = os.getenv("LLM_MODEL")
```

## 允许的标准库

`json` `re` `math` `os`(文件) `sys` `time` `datetime` `urllib` `base64` `hashlib`
`collections` `functools` `itertools` `pathlib` `tempfile` `glob` `argparse`

> 不要依赖第三方 **python 包**。平台沙箱只保证标准库。
> **例外 · 系统二进制**：`ffmpeg`/`ffprobe` 由沙箱提供，经 `subprocess` 调用（不是 python 包）——媒体探测/抽帧/转码/音频分析用它，不要引 `cv2`/`numpy`/`imageio-ffmpeg` 等第三方包（沙箱没有）。

## 命名对齐（迁移心智）

| 本地打样 | 迁移到平台 |
|----------|------------|
| `call_platform_api(api_code, body)` | **完全不变** —— 平台沙箱注入同名内置函数 |
| `blue_exec_api(api_code, body)` | Agent 的 `blue_exec_api` 工具调用 |
| `blue_query_api_docs(api_code)` | Agent 的 `blue_query_api_docs` 工具调用 |
| `register_async_poll(query_api, params, completion_config=…)` | Plugin 本地用 Runtime Core `wait_result`；平台内运行时使用其异步原语 |

迁移时：脚本原样上传，`call_platform_api(...)` 行不变，没有桥接块可删。旧草稿遗留的标记桥接块仍会在 `ideaswork skill push` 的上传副本中剥离；平台自行维护 `__skill_meta.json`，推送只生成待审核版本（由属主在 Studio 版本历史接受），不自动发布。
