"""JSON output helper for --json flag."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))  # noqa: T201


def exit_with(result_dict: dict[str, Any], ok: bool, exit_code: int = 1) -> None:
    print_json(result_dict)
    sys.exit(0 if ok else exit_code)
