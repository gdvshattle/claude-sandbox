#!/usr/bin/env python3
"""
PreToolUse hook — whitelist approach.
Blocks all file tool access outside $CLAUDE_PROJECT_DIR.
Exit 2 = hard block (fed to Claude as error). No JSON output — avoids known bug
where permissionDecision:deny in JSON is ignored for Edit tool (issue #37210).
"""

import json
import os
import sys
from pathlib import Path

# Tool → field(s) that contain the target path, in priority order
PATH_FIELDS = {
    "Read":      ["file_path"],
    "Write":     ["file_path"],
    "Edit":      ["file_path"],
    "MultiEdit": ["file_path"],
    "Glob":      ["pattern", "path"],
    "Grep":      ["path", "include"],
}

def resolve_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name  = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    fields = PATH_FIELDS.get(tool_name)
    if not fields:
        sys.exit(0)

    project_dir = resolve_path(
        os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    )

    for field in fields:
        raw = tool_input.get(field, "")
        if not raw:
            continue

        path_part = raw.split("*")[0].rstrip("/") or raw
        if not path_part:
            continue

        target = resolve_path(path_part)

        try:
            target.relative_to(project_dir)
        except ValueError:
            print(
                f"BLOCKED: '{target}' is outside project dir '{project_dir}'. "
                f"Only paths inside the project dir are allowed.",
                file=sys.stderr
            )
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
