"""
<脚本名>.py — <一句话说明这个薄脚本做什么>

【薄脚本铁律】只做纯计算（LLM 文本生成 / TTS 合成 / 数据整形）。
业务编排（调哪些 API、顺序、依赖、异步等待）由 Agent 在 SKILL.md 里负责，
脚本内**禁止**堆编排逻辑、**禁止** while+sleep 死等异步任务。

用法（本地与平台是同一份代码，无需任何改写）：
    --model <model_name> --input <in.json> --output <out.json>

`call_platform_api(api_code, body)` 是运行时注入的内置函数，不要 import，也不要自己写桥接/兜底代码。
本地验证用 `ideaswork runtime python --workspace <草稿目录> --script tools/<脚本名>.py --args-json @args.json`，
它注入的函数与平台同名同签名；不要直接 `python tools/<脚本名>.py`（裸跑没有注入，会 NameError）。
"""
import argparse
import json
import sys


def _die(msg: str, code: int = 1) -> None:
    """统一错误出口：错误信息打到 stderr，非零退出，让 Agent 能捕获失败。"""
    print(f"[<脚本名>][ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def run(args) -> dict:
    """核心纯计算。失败用 raise 抛异常，由 main 统一兜底。

    示例：调一个平台 API 把自由文本变成结构化结果。
    """
    body = {
        "model": args.model,
        # ... 按 blue_query_api_docs 得到的 request_schema 填必填字段 ...
    }
    result = call_platform_api("<api_code>", body)  # noqa: F821 — 运行时注入的内置函数
    # 按真实 response 结构取值（schema 不可信时以一次真实调用为准）
    content = result["choices"][0]["message"]["content"]
    return json.loads(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="<脚本说明>")
    # 运行时配置一律走命令行参数；禁止用 os.environ / os.getenv（平台多会话共享进程会污染）
    parser.add_argument("--model", required=True, help="LLM 模型名（PM 确认可用值）")
    parser.add_argument("--input", help="输入文件路径（JSON）")
    parser.add_argument("--output", required=True, help="输出文件路径（JSON）")
    args = parser.parse_args()

    try:
        result = run(args)
    except KeyError as e:
        _die(f"响应结构缺字段 {e}（schema 可能与真实返回不符，请按真实调用修正取值路径）")
    except Exception as e:  # noqa: BLE001 — 薄脚本统一兜底，保证失败可见
        _die(f"执行失败：{e}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # stdout 约定：人类可读状态行用 [脚本名] 前缀；结构化结果只写 --output 文件，不打印到 stdout
    print(f"[<脚本名>] 已写入: {args.output}")


if __name__ == "__main__":
    main()
