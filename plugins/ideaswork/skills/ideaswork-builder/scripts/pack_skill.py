#!/usr/bin/env python3
"""Pack a local Skill draft into the zip the Remote MCP push route expects.

Pure standard library, no credentials: it only reads the draft and writes a zip. Uploading is a separate
step (curl with the runtime lease on stdin, see the Builder Skill). The server's own gate stays the
authority; this script only refuses what the server would also refuse, *before* anything is uploaded, and
leaves out files that must never leave the machine.

    python3 pack_skill.py <draft_dir> <out.zip>

Prints one JSON object on stdout. Exit status: 0 packed, 1 refused (the output file is removed), 2 bad usage.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile

# Local ledgers, caches and platform-owned metadata. ``__skill_meta.json`` is platform-owned (a pusher must
# not forge it); the server drops it too.
IGNORED_NAMES = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".DS_Store", ".avp_run", ".avp_gaps.json",
    "SKILL_BUILD_FINDINGS.md", "__skill_meta.json", "avp_local",
})
IGNORED_PREFIXES = (".avp_gaps.json.",)

# The server's safe-unzip limits (src/skills/skill_archive.py) and the push route's 20 MiB archive cap.
MAX_FILES = 2000
MAX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024

BRIDGE_START = "# === avp_local 打样桥接"
BRIDGE_END = "# === 打样桥接结束 ==="


class Refused(Exception):
    pass


def _ignored(name: str) -> bool:
    return name in IGNORED_NAMES or name.startswith(IGNORED_PREFIXES)


def _check_python_source(path: str, relative: str) -> None:
    """A draft that still carries the old bridge block must be cleaned by hand: this script never edits code."""
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("Python 源码必须是 UTF-8：" + relative)
    if any(line.strip().startswith(BRIDGE_START) or line.strip() == BRIDGE_END for line in text.splitlines()):
        raise Refused("%s 仍含旧的 avp_local 打样桥接块（`%s` … `%s`）；删除整块后再打包，`call_platform_api` 调用行保持不变"
                      % (relative, BRIDGE_START, BRIDGE_END))


def pack(draft: str, out: str) -> dict:
    root = os.path.realpath(draft)
    if not os.path.isdir(root):
        raise Refused("草稿目录不存在：" + draft)
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        raise Refused("草稿缺少 SKILL.md")
    out_real = os.path.realpath(out)
    if out_real == root or out_real.startswith(root + os.sep):
        raise Refused("输出 zip 不能放在草稿目录里：它会把自己打进包里")

    files = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # A symlinked directory is neither followed nor listed in ``filenames``; dropping it silently would
        # push a Skill that is missing content, so refuse it like a symlinked file.
        for name in list(dirnames):
            if _ignored(name):
                continue
            if os.path.islink(os.path.join(dirpath, name)):
                raise Refused("草稿含符号链接目录：" + os.path.relpath(os.path.join(dirpath, name), root))
        dirnames[:] = sorted(name for name in dirnames if not _ignored(name))
        for name in sorted(filenames):
            if _ignored(name):
                continue
            path = os.path.join(dirpath, name)
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path) or not os.path.isfile(path):
                raise Refused("草稿含符号链接或非普通文件：" + relative)
            if relative.endswith(".py"):
                _check_python_source(path, relative)
            total += os.path.getsize(path)
            files.append((path, relative))
            if len(files) > MAX_FILES or total > MAX_UNPACKED_BYTES:
                raise Refused("草稿超出安全上限（最多 %d 个文件、解压后 %d MiB）" % (MAX_FILES, MAX_UNPACKED_BYTES // 1024 // 1024))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in files:
            archive.write(path, relative)
    size = os.path.getsize(out)
    if size > MAX_ARCHIVE_BYTES:
        raise Refused("打包后 %d 字节，超过推送上限 20 MiB" % size)
    return {"success": True, "archive": out, "size_bytes": size, "file_count": len(files), "files": [rel for _, rel in files]}


def main(argv: list) -> int:
    if len(argv) != 3:
        print(json.dumps({"success": False, "error_code": "invalid_arguments",
                          "error": "usage: pack_skill.py <draft_dir> <out.zip>"}, ensure_ascii=False))
        return 2
    draft, out = argv[1], argv[2]
    try:
        result = pack(draft, out)
    except Refused as refusal:
        try:
            os.remove(out)
        except OSError:
            pass
        print(json.dumps({"success": False, "error_code": "validation_failed", "error": str(refusal),
                          "next_action": "fix_draft_and_retry"}, ensure_ascii=False))
        return 1
    except OSError as error:
        try:
            os.remove(out)
        except OSError:
            pass
        print(json.dumps({"success": False, "error_code": "local_io_error",
                          "error": "%s: %s" % (error.strerror or "I/O error", error.filename or "")},
                         ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
