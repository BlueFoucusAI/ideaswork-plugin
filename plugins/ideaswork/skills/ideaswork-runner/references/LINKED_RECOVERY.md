# linked 子技能缺失时的恢复

本节只用于原 Skill 明确要求的子技能没有随主包下发、下载失败或未物化的情况；正常主路径
仍一次消费主 `pull_skill` 返回的完整 `linked[]`，不逐个重复拉取已经可用的子技能。

## 先尝试补拉，再决定是否停止

1. 核对主 pull 响应和本地运行目录。已下发 checkout、只是本地未物化的，先复用该 checkout
   下载并物化，不重新 pull。不要仅凭 `linked=[]` 就判定服务部署或关联配置异常。
2. 确认缺失技能的身份：优先使用原 Skill 或关联元数据里的 `skill_id`；只有名称时，查询
   `get_skill_catalog_records`，把原 Skill 明确给出的名称解析为唯一可访问 id。此查询仅用于
   已知依赖的身份核对，不是重新展示 Catalog；内部 CLI 包可能不在面向用户的 Catalog 中。
   找不到时报告查询结果；同名多项时让用户确认，不猜 id 或替代技能。
3. 在当前 `skill_runner` Context 调用 `pull_skill(skill_id=<缺失技能id>)`。每个已确认的缺失
   技能先尝试一次，不为补拉切换团队、扩大权限或新建会话；不要自动修改平台关联配置。
   返回的递归 linked checkout 也要一并消费，不再逐个重复 pull。
4. 补拉成功后，将子技能及它返回的依赖物化到原主 Skill 的 workspace，不创建独立运行目录：

   ```text
   ideaswork runtime checkout --workspace <原workspace根目录>
       --skill-name <子技能名> --checkout-id <子checkout_id>
       --primary-skill-name <原主Skill名>
       --runtime-endpoint <endpoint> --runtime-lease-stdin
   ```

   对补拉响应里的递归 linked checkout 使用相同的 `--primary-skill-name`。这里的
   `--workspace` 是初次 checkout 使用的根目录，不是其输出的 `workspace_dir`。
   复用当前有效 runtime lease；Host 更新主 Skill 的依赖记录及受管 prompt，保留主 Skill
   文件、既有产物和 Context。若初次 pull 未完成，先恢复主 checkout，再继续原阶段。
5. 只有补拉、下载或身份核对仍失败时，才停止受影响阶段并报告具体原因（找不到、名称歧义、
   无权访问、未发布/未启用、归档不可用或网络错误等）及已尝试的操作。不要无限重试，
   不把所有失败都归因于部署异常，也不在未尝试补拉前擅自用内置脚本替代必需依赖。

补拉是显式恢复路径，不改变正常 pull 的完整依赖校验，也不允许执行一个缺少必需依赖的阶段。
