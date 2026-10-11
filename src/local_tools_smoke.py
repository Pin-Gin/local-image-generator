from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_ai_tools import LocalAIToolbox


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local Git/Oracle tool foundation")
    parser.add_argument("--require-oracle", action="store_true")
    args = parser.parse_args()

    toolbox = LocalAIToolbox(ROOT, ROOT / "config" / "local_tools.json")

    git_status = toolbox.git.status("local-image-generator")
    print("[LOCAL-TOOLS:GIT:OK]")
    print(git_status["status"])

    status = toolbox.status()
    print("[LOCAL-TOOLS:STATUS]")
    print(json.dumps(status, ensure_ascii=False, indent=2))

    oracle = status.get("oracle", {})
    if args.require_oracle:
        if not oracle.get("online"):
            raise RuntimeError(f"Oracle is required but not online: {oracle}")
        print(
            f"[LOCAL-TOOLS:ORACLE:OK] schema={oracle.get('schema')} version={oracle.get('schema_version')}"
        )
    elif oracle.get("online"):
        print(
            f"[LOCAL-TOOLS:ORACLE:OK] schema={oracle.get('schema')} version={oracle.get('schema_version')}"
        )
    else:
        print("[LOCAL-TOOLS:ORACLE:SKIP] Oracle is not online/configured yet")

    print("[LOCAL-TOOLS:SMOKE:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
