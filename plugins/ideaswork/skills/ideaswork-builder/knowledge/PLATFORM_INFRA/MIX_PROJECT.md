# PLATFORM_INFRA/MIX_PROJECT — 混剪工程编排（平台侧隐含知识）

> 按需加载：用到本分类能力时才读（见 `knowledge/README.md`）。
> 只记「看 API 文档猜不到、踩过才知道」的坑。字段完整用法以 `blue_query_api_docs` 的 schema 为准。

混剪工程链路：`project`（容器）→ `mproject`（工程，本分类）→ `shooting`（分镜，在 `PLATFORM_INFRA/STORYBOARD`）→ `mproject_clip_add`（往分镜塞视频切片）。查询几乎都从 **`mproject_detail`** 进。

## 创建工程后有 3 个默认空分镜，不是 1 个

`mproject_create` 成功后系统自动生成 **3 个**空分镜（index 0/1/2）。写入自己的 scene 前**必须先删干净这 3 个**，否则成片顺序错乱。

## shooting_add 没有 name / index 参数，顺序 = 调用顺序

`shooting_add`（`PLATFORM_INFRA/STORYBOARD`）无法指定位置（只有 `mix_project_id` + 可选 `shooting_type`）。分镜排序**完全由调用顺序决定**——按 scene_1 → scene_2 → … 依次调即可。

## 清理多余分镜要删 index 最大的

`shooting_add` 重复/异常会产生多余分镜。清理时把 `shooting_list` 按 `index` **降序**排，删前 `(actual - expected)` 个（即 index 最大的几个）。**不能按 index 升序删**——会误删已绑定视频的有效分镜。

## mproject_update 只改名，响应 data 是空 dict

`mproject_update` 的响应 `data` 为 `{}`，**不含 shooting_list**。要拿分镜列表只能另调 `mproject_detail`。

## mix_project_config_id 只能从 mproject_detail 取

`mproject_config_update` 必填 `mix_project_config_id`，但 `mproject_create` / `mproject_update` 的响应里都没有它。唯一来源：`mproject_detail` 返回的 `data.mix_project_config.mix_project_config_id`。

## mix_project_id / shooting_id 全程是 int

所有接口的 `mix_project_id`、`shooting_id` 均为 **int**，取值后不要转成字符串。

## 全局字幕：完成判断轮询 mproject_detail，不是 task_detail

`mproject_captions_generate` 生成全局字幕，两个坑：

- **前置**：先 `mproject_config_update` 配好 `global_audio_config`（TTS 需 `vlc_id` 已绑定），并开 `global_captions_switch: true`；否则无音频基准，生成不出字幕。
- **完成判断不走 `task_detail` 轮询**——改轮询 `mproject_detail` 的 **`data.global_captions`** 字段是否存在（非空即完成）：

```yaml
register_async_poll:
  tasks:
    - query_api_code: mproject_detail
      query_params: { mix_project_id: <mix_project_id> }
      completion_config: { field: "data.global_captions", op: "exists" }
      poll_interval: 10
      max_polls: 30
  completion_policy: "all"
```

> 触发时 body 传 `mix_project_id` + `style`（如 `"Highlight"`）。

## 导出/压制前必须先 mproject_preview

`mproject_preview` 触发备片预览生成；**导出成片或获取备片列表前必须先调**（`artwork_save`/`candidate_export` 等）。备片已最新时它会返回「无需重新生成」提示。

## 工程详情只给已绑定素材——项目素材库要另调 material_list

`mproject_detail` 只返回分镜里**已绑定**的切片素材，给不到「项目素材库全量」。要枚举/检索项目素材库用 **`material_list`**（在 `PLATFORM_INFRA/MATERIAL`）：必填 `project_id`，支持 `material_type` / `tag_list` / `user_tag_list` / `custom_tag_ids` / `filter_material_tag_list` / `material_name` / 分页 / `sortBy`——所以「按标签自动选材」是**可以做**的。

- `material_list` 的 `response_schema` 含未展开的 `$ref`（`blue_query_api_docs` 会给 `schema_warnings`），素材项字段以一次真实调用为准。
- **写侧仍有缺口**：素材**没有标签写入接口**（MATERIAL 分类只有 `detail`/`list`/`parse`/`trim_audio`/`url_add`/`image_add`/`upload_proxy`/`remove_background_*`）。「把投放结论回写成素材标签」若是核心目标且无输出文件等合理绕过方案，才记为阻塞的 `missing_api` 平台能力问题；否则调整 Skill 流程或写入遗留说明，不必提报。

> 校验：dev 环境 2026-08-10 实查注册表。**注册表会变**——真要依赖读侧时，先查看当前 Context 的 `blue_list_apis` grant，再逐个用 `blue_query_api_docs` 核对相关读侧 API；不可见不等于注册表缺失。
