from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .commands import decide, evaluate, rebuild
from .config import load_settings


_COMMANDS = {
    "decide": decide,
    "evaluate": evaluate,
    "rebuild": rebuild,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-trading-lab")
    parser.add_argument("command", choices=sorted(_COMMANDS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    result = _COMMANDS[args.command](settings)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
