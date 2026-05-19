from __future__ import annotations

import argparse
from pathlib import Path

from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nac-web",
        description="Lokaler Webserver für grafische NaC-Ausgaben.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Pfad zum Repository-Root.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind-Adresse. Standard: 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8765, help="Port. Standard: 8765.")
    parser.add_argument("--open", action="store_true", help="Browser nach Serverstart öffnen.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_server(args.repo_root, args.host, args.port, open_browser=args.open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
