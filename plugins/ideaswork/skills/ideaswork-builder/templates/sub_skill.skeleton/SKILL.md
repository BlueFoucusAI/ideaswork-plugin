# sub_skill_NN_<语义> — <这一步做什么>

## 目标

<一句话：这个 sub_skill 完成业务流程里的哪一步，产出什么交给下一步>

## 前置条件

- <上一个 sub_skill 的产出，如「sub_skill_01 已产出 blueprint.json」>
- <本步要用的 api_code 已在 sub_skill_02 `blue_query_api_docs` 验证过>

## 步骤

### 1. <动作>

调用 `<api_code>`（类型：exec/query）。入参要点：

- `<字段>`：来源 = <用户输入 / 上一步返回的 xxx>
- 异步：<同步 / 用 register_async_poll 等 `<query_api>`，完成条件 `<field op value>`>

> 用 YAML/自然语言描述调用，**不要写 Python 伪代码**（无 f-string、列表推导、函数调用语法）。

### 2. <若需纯计算（LLM/TTS/整形），用薄脚本>

从 `templates/thin_script.template.py` 起步，命名 `tools/<动作>.py`：
- 命令行参数传配置；直接调用运行时注入的 `call_platform_api`，不需要桥接块。
- 产出写 `--output` 文件，供 Agent 下一步引用。

## 产出

<明确交给下一个 sub_skill 的东西，如「assets.json，含每个素材的 material_id」>
