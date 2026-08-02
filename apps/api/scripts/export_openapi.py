"""Dump OpenAPI JSON for the web TypeScript generator.

Usage (from repo root):
  cd apps/api && uv run python scripts/export_openapi.py ../web/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from portfolio_tracker.main import create_app


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path("-")
    doc = create_app().openapi()
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if str(out) == "-":
        sys.stdout.write(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
