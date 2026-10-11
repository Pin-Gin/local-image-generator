from __future__ import annotations

import argparse
from pathlib import Path

from json_parts import load_json_part


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that a local reusable JSON part can be resolved")
    parser.add_argument("--ref", required=True, help="part:<part_id>@<version>")
    args = parser.parse_args()

    part = load_json_part(ROOT, args.ref)
    print(f"[JSON-PART:READ:OK] ref={part.ref}")
    print(f"part_type={part.part_type}")
    print(f"name={part.name}")
    print(f"path={part.path}")
    print(f"sha256={part.sha256}")
    print(f"positive={part.positive}")
    print(f"negative={part.negative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
