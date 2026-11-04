# `ask_user_interact` 动态表单写法规范

调用前先读本节。表单渲染失败几乎都是**参数形态**问题：键名写错、值类型写错、少了必填键、把对象写成字符串。
只使用本文出现的参数与字段键；不确定的键不要自创。

## 1. 先决定要不要弹表单

| 情况 | 做法 |
|---|---|
| 用户原话和 API 文档默认值已能确定全部参数 | 不弹，直接调用 |
| 只缺一个简单选择，或只是确认“是否继续” | 在对话里用文字问 |
| 缺 ≥2 个结构化字段、要选规格、要选素材 | 弹**一张**表单 |

- **一次问全**：缺的字段、素材字段放进同一张表单，不分多张、不分多轮追问。
- 选项、取值范围必须来自 `blue_query_api_docs` 返回的真实枚举/限制，不编造 API 不接受的取值。
- 已能确定的值用 `value` 预填；不替用户做需要他决定的选择（尤其计费、素材、规格）。

## 2. 调用骨架

```text
ask_user_interact(mode="form", title="<简短标题>", tabs=[
  {"key": "<tab_key>", "label": "<标签>", "fields": [ <字段对象>, ... ]}
])
```

- 顶层只用 `mode`、`title`、`tabs`。`tabs` 是**数组对象**，不是 JSON 字符串；每个 tab 必须有 `key`、`label`、`fields`。
- `mode`：`form`（默认，要用户填/确认）或 `preview`（纯展示，无按钮）。
- `form` **每轮最多一次，调用后本轮立即结束**：说明文字放在调用**之前**，调用后不再输出文字、不再调用工具。
  用户提交后以普通消息 `interaction_response`（含 `interaction_id`、`action`、`data`）回到对话。
- `preview` 不结束本轮，可继续输出或调用其他工具。
- 所有 `key` 用小写英文 + 下划线（`aspect_ratio`），tab 内不重复。每个非 `info` 字段都写 `label`（用户的语言）。
- 一张表单通常一个 tab 就够；每个 tab 建议不超过 10 个字段，最多 10 个 tab。不传文件路径，不传本地 MCP 的 `path`。

## 3. 字段类型速查（共 10 种，别无其他）

| `type` | 必备键 | `value` 的 JSON 类型 | 备注 |
|---|---|---|---|
| `text` | `key` `label` | 字符串 | 单行；引导灰字用 `placeholder` |
| `textarea` | `key` `label` | 字符串 | 多行，如提示词 |
| `number` | `key` `label` | **数字**（不是 `"3"`） | 可加 `min` / `max` |
| `range` | `key` `label` `min_limit` `max_limit` | `{"min": 数字, "max": 数字}` | 边界用 `min_limit`/`max_limit`，不是 `min`/`max` |
| `select` | `key` `label` `options` | 某个选项的 `value` | 单选 |
| `multi_select` | `key` `label` `options` | 选项 `value` 的**数组** | 多选 |
| `checkbox` | `key` `label` | **布尔** | `true` / `false`，不是字符串 |
| `info` | `key` `content` | 无 | 只写 `content`（markdown），**不写** `label`/`value` |
| `media_info` | `key` `value` | `{"url": 心影 CDN HTTPS 地址, "name": 名称, "media_type": "image"/"video"/"audio"/"other"}` | 只用于展示已有媒体 |
| `built_in` | `key` `label` `component` | 一般不预填 | 仅 `component: "material_picker"`，见 §4 |

- `options` 是对象数组：`[{"label": "用户看到的文字", "value": "回传并交给 API 的取值"}]`。`label` 与 `value` 都必须有。
  回传的是 `value`；调用 API 时用 `value`，不要拿 `label` 去填参数。
- 默认值/建议值写 `value`；`placeholder` 只放引导灰字，不放默认值。
- 必填写 `"required": true`；补充说明写 `description`。

## 4. 素材字段（表单内选素材）

```text
{"key": "bgm", "type": "built_in", "component": "material_picker", "label": "背景音乐",
 "accept": ["audio"], "multi": false, "required": true}
```

- 必须是 `type: "built_in"` + `component: "material_picker"`；不要写 `type: "material_picker" / "file" / "upload" / "image"`。
- `accept` 只允许 `video / image / audio / ai_video / ai_image / ai_audio`；可选 `multi`、`material_type`（须在 `accept` 内）、`query`。
- 要求当前会话已绑定工作区；先确认 Context 再弹。选择发生在表单内，Agent 不为选素材调用 `browse_materials`。
- 回传 `data` 中该字段为素材对象（`multi` 时为数组），含 `material_id / name / url / material_type / cover_url`。
- 仅当表单发出 `material_pick_request`（宿主不支持 App 内取数）时，才用 `browse_materials` 在对话里列候选，
  等用户文字确认后把所选素材写回该字段的 `value`、其余字段按 `draft` 回填，再重新调用 `ask_user_interact`。

## 5. Few-shot（照抄结构，只替换内容）

✅ 视频生成参数：文本 + 选择 + 数字 + 可选素材 + 提示（选项取值须来自 API 文档，此处仅示意）：

```text
ask_user_interact(mode="form", title="视频生成参数", tabs=[
  {"key": "basic", "label": "基础参数", "fields": [
    {"key": "prompt", "type": "textarea", "label": "视频描述", "required": true,
     "placeholder": "例如：海边日落，镜头缓慢推进"},
    {"key": "aspect_ratio", "type": "select", "label": "画幅", "required": true, "value": "16:9",
     "options": [{"label": "横屏 16:9", "value": "16:9"}, {"label": "竖屏 9:16", "value": "9:16"}]},
    {"key": "duration", "type": "number", "label": "时长（秒）", "value": 5, "min": 3, "max": 10, "required": true},
    {"key": "ref_image", "type": "built_in", "component": "material_picker", "label": "参考图（可选）",
     "accept": ["image"], "multi": false},
    {"key": "tip", "type": "info", "content": "提交后开始生成，会消耗额度。"}
  ]}])
# 调用后立刻结束本轮。下一轮从用户消息的 interaction_response.data 按字段 key 读取；缺失的字段视为用户未填，不自行补值。
```

✅ 选择工作区（选项必须来自本次 `browse_contexts`，`value` 填该选项本次的 `context_ref`）：

```text
ask_user_interact(mode="form", title="选择工作区", tabs=[
  {"key": "workspace", "label": "工作区", "fields": [
    {"key": "context_ref", "type": "select", "label": "团队 / 项目", "required": true,
     "options": [
       {"label": "团队A / 项目1", "value": "<本次 browse_contexts 返回的 context_ref>"},
       {"label": "团队A / 项目2", "value": "<本次 browse_contexts 返回的 context_ref>"}]}]}])
```

✅ 多选、开关、区间：

```text
ask_user_interact(mode="form", title="导出设置", tabs=[
  {"key": "export", "label": "导出", "fields": [
    {"key": "formats", "type": "multi_select", "label": "导出格式", "value": ["mp4"],
     "options": [{"label": "MP4", "value": "mp4"}, {"label": "GIF", "value": "gif"}]},
    {"key": "watermark", "type": "checkbox", "label": "添加水印", "value": false},
    {"key": "clip", "type": "range", "label": "截取区间（秒）", "min_limit": 0, "max_limit": 30,
     "value": {"min": 0, "max": 10}}]}])
```

✅ 展示成片（`preview`，不阻塞，不结束本轮）：

```text
ask_user_interact(mode="preview", title="成片预览", tabs=[
  {"key": "out", "label": "预览", "fields": [
    {"key": "clip", "type": "media_info", "label": "成片",
     "value": {"url": "https://blueai-video-global.bluemediacdn.com/out.mp4", "name": "成片.mp4", "media_type": "video"}}]}])
```

## 6. 常见错误 → 正确写法

| 错误 | 正确 |
|---|---|
| `tabs="[{\"key\":…}]"`（整体序列化成字符串） | 直接传数组对象 |
| 顶层直接放 `fields`，没有 `tabs` | `tabs=[{"key","label","fields":[…]}]` |
| tab 缺 `label` 或 `key` | 每个 tab 三项齐全：`key`、`label`、`fields` |
| 字段用 `name` / `title` / `default` / `choices` / `enum` / `items` / `multiple` | 用 §3 里的键：`key` `label` `value` `options` `required` `description` `placeholder` `content` `accept` `multi`；schema 里没有那些键 |
| `type` 写成 `string` / `integer` / `boolean` / `radio` / `dropdown` / `file` / `image` / `upload` | 只能是 §3 的 10 种 |
| `options: ["横屏", "竖屏"]`（字符串数组） | `[{"label": "横屏", "value": "landscape"}, …]` |
| `select` / `multi_select` 缺 `options` | 必须有且非空 |
| `number` 的 `value` 写 `"5"`；`checkbox` 写 `"true"`；`multi_select` 写 `"mp4"` | 数字、布尔、数组 |
| `range` 用 `min`/`max` 表示边界 | 边界 `min_limit`/`max_limit`，选中值 `value:{"min":…,"max":…}` |
| `info` 字段写 `label` 或 `value` | `{"key":"tip","type":"info","content":"…"}` |
| 默认值写进 `placeholder` | 默认值写 `value` |
| `media_info` 的 `value` 传 URL 字符串或本地路径 | 对象，且 `url` 是心影 CDN 的 HTTPS 地址；其他文件先上传素材库 |
| 素材写成 `type:"material_picker"`，或用 `built_in` 的其他组件、`material_preview`、`session_file` | `type:"built_in"` + `component:"material_picker"` |
| 同一 tab 或同一表单内 `key` 重复 | 全部唯一 |
| `form` 调用后继续输出文字或调用工具；同一轮调第二次 `form` | 调用即停；第二张放到用户提交后的下一轮 |
| 用 `label` 的文字去填 API 参数 | 用回传的 `value` |
| 为选素材调用 `browse_materials`，或收到回传后调用提交/状态工具 | 表单内自己选；收到 `interaction_response` 直接继续 |
| 替用户猜测或提交答案 | 只预填已确定的默认值；选择以用户回传为准 |

## 7. 提交前自检（每次都过一遍）

1. `tabs` 是数组，且每个 tab 有 `key`、`label`、`fields`。
2. 每个字段有 `key`、`type`，`type` 在 10 种之内；非 `info` 字段有 `label`。
3. `select` / `multi_select` 的 `options` 是 `{label, value}` 对象数组，取值来自 API 文档。
4. `value` 的 JSON 类型与 §3 一致（数字、布尔、数组、对象不要写成字符串）。
5. 素材字段是 `built_in` + `material_picker`，`accept` 在允许值内，且已确认工作区。
6. `info` 只有 `content`；默认值在 `value`，不在 `placeholder`。
7. 所有 `key` 唯一；整张表单不超过 10 个 tab、每个 tab 不超过 10 个字段。
8. `form`：说明文字已放在调用前，调用后不再输出、不再调用工具。

回传后：核对 `interaction_id`；仅在 `action=confirm` 时据 `data` 继续，不再确认用户刚刚已经确认过的内容；
取消则停止相应动作，不重复弹同一张表单。
