# 本地素材上传

- 用户指定本地文件、或 Skill 需要将本地产物入素材库时，复用 `material_upload_proxy`。
  先确认当前 Context 和 API 文档/grant，不能把本机文件路径直接发给 `blue_exec_api`。
- Remote MCP 模式：从当前 MCP 的 `create_runtime_lease`（或 pull 返回）取得 lease，
  通过随包启动脚本执行 `runtime/bin/ideaswork material upload <文件> --runtime-endpoint <地址>
  --runtime-lease-stdin --json`；lease 经 stdin 传入，不写入文件/日志或环境变量，
  不要求独立 CLI 登录。
- 显式 lease 缺失/过期：通过当前 MCP 获取新的 lease；Context 改变先确认 Context。
  不自动改用 CLI 自己的账号，也不因权限拒绝切换入口。
- 独立 CLI 模式：`ideaswork material upload <文件> --json` 使用 CLI 自己已有登录和
  task Context，内部获取 lease。复用同一 `--task`，不自动选择项目或扩展 grant。
- Runtime 执行 Skill 脚本时，原 `__call_platform_api_file:<workspace相对路径>` 写法
  保留；父进程负责上传，子进程不接收 lease。上传返回 material_id，不再补一次上传 API。
- 超时/结果未知不自动重传，先检查素材库，避免重复创建素材。
