#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from typing import Any


def main() -> int:
    payload = _read_payload()
    command = str(payload.get("command") or payload.get("tool_input") or "")
    hints = []
    if "quality_gate.py" in command or "nac.py doctor" in command:
        hints.append("Strict quality-gate evidence is suitable completion evidence.")
    if "gh pr merge" in command:
        hints.append("Confirm owner approval before merging pull requests.")
    if "git push origin --delete" in command or "git branch -d" in command:
        hints.append("Branch cleanup is destructive and must be owner-approved.")

    print(json.dumps({"status": "ok", "hints": hints}, ensure_ascii=True))
    return 0


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw[:200]}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


if __name__ == "__main__":
    raise SystemExit(main())

