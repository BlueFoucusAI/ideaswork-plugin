# AI_INFRA/TEXT2VIDEO — 生图/生视频任务（平台侧隐含知识）

> 按需加载：用到本分类能力时才读（见 `knowledge/README.md`）。
> 只记「看 API 文档猜不到、踩过才知道」的坑。字段/枚举/模式完整用法以 `blue_query_api_docs` 的 schema 与 `model_list` 为准。

核心接口 **`t2v_session_task_create`**（提交，出可二次编辑的「生成卡片」）+ **`t2v_session_task_query`**（轮询）。选模型/模式靠单字段 **`model_variant`**（格式 `<model>:<inner_task_type>`，取值先查 `model_list`，勿硬编码）。

## project_id 由平台自动注入

`model_variant` 之外唯一「必填」的 `project_id`，**调用时无需自己传**——平台运行时补齐（薄脚本迁移后同理）。

## 支持的模式随模型而异，以 model_list 为准

生视频有多种驱动模式（`img2video` / `reference2video` / `start-end2video` / `videoextend` 等）；**纯文生视频（text2video，无图驱动）是否可用取决于具体模型**——多数模型支持，但**部分模型（如 Vidu）要求必须有图/参考驱动**，不能纯文字生视频。别把某个模型的限制当成全平台通例，选模型/模式前先查 `model_list` 确认该模型支持的后缀。

## prompt 和 text 必须同时传，内容完全一致

后端按 `prompt→text→input` 优先级取值做实际生成；前端对话历史回显读 `text`。只传其一 → 前端裂图或对话记录不一致。

- `input` 字段已废弃，禁止使用。
- prompt 若由上游脚本精调产出，**原封不动传，严禁 Agent 二次修改**（改了效果变差）。

## 普通图素材必须同时传 material_id + cdn_url

`material_id` 供后端生成，`cdn_url` 供前端会话卡片回显——**缺 `cdn_url` 前端裂图**，两者必须成对。Portrait 人脸资产没有 `material_id`，传 `source_asset_id` + `cdn_url`。

> `firstFrame` / `tailFrame` 每项结构同 `image`，同样规则；数组**只取第一个元素**，多传无效。

## audio 的 source_info 需手动构造

`tts_engine_voice_design`、`material_trim_audio` 的返回值**不带 `source_info`**，缺了前端无法播放。需手动补（`assemble_video_params.py` 的 `_ensure_audio_source_info()` 会兜底，直接调 API 时自己补）：

```json
"source_info": { "SourceInfo": {
  "NormalizedFileType": "audio",
  "NormalizedFormat": "mp3",   // 从 cdn_url 后缀取，识别不了兜底 "mp3"
  "Duration": 8.5              // 取 audio_len（秒）
}}
```

## action:"diffusion" 是 MJ 旧路径，不要传

图片生成用 `model_variant:"<model>:txt2img"`，**不需要 `action` 字段**。`action` 枚举（diffusion/remix/upscale…）是遗留的 MJ 硬分支路径，`submit_asset_image.py` 实际并不传。

## reference2video vs start-end2video 互斥，别混传

- `reference2video`：提供参考图（`image` 列表），模型自由发挥运动，`firstFrame`/`tailFrame` 传空数组。
- `start-end2video`：严格锁定首尾帧，模型补中间，`image` 传空数组，`firstFrame`/`tailFrame` 必传。

混传会导致行为混乱。

## 图片任务不传 duration

`duration` 仅视频生效，图片任务传了无效（图片用 `image_generation_numbers` 控制张数）。

## Seedance 全能参考：参考音频总时长 ≤ 15s

放进同一个 Seedance 全能参考的音频总时长上限 15s。N 条会超时，用 `material_trim_audio`（`PLATFORM_INFRA/MATERIAL`，非破坏性、返回**新 material_id**）把**每条**裁到 `15/N` 秒（`max_sec=15/N`，两位小数），把裁剪后的新 id 传进去。仅支持 `audio`/`ai_audio`。

## 响应有双层 data 嵌套

```
avp_event_id  → data.avp_event_id
base_task_id  → data.data.base_task_id   ← 注意双层，取错层是常见坑
```

## 轮询要点

- `check_event_ids` 是**逗号拼接字符串**，不是数组：`"evt-001,evt-002"` ✅ / `["evt-001",...]` ❌。
- `t2v_session_task_create` 的 `success_condition` 注册表为 null，用 `register_async_poll` 须**显式传** `completion_config`（如 `{field:"data.summary_task", op:"eq", value:0}`）。
- `t2v_session_task_query` 的 `request_schema` 为空（注册表残缺，非真无参），必填项以一次真实调用确认。
- `max_polls`：视频约 7-15 分钟（≈80），图片可小（≈30）；`poll_interval` ≈ 30s。

## 产出直接喂下游

query 成功返回视频链接 + 产出素材 `material_id`，该 id 可直接喂下游（如 `mproject_clip_add` 把生成视频作为切片加进混剪工程）。

## 打样注意：视频渲染昂贵耗时

打样阶段别真跑大量生成；验证调用链单条小参数试跑即可，轮询量级见 `CONSTRAINTS.md`「视频渲染」行，上线前按真实耗时校准。
