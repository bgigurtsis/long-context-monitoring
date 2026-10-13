"""Dispatch the public generation, insertion, and monitoring commands."""
from __future__ import annotations
import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from long_context_monitoring.textio import force_utf8_stdio


def main(argv: list[str] | None = None) -> int:
    """Run the chosen component with its own argument parser."""
    force_utf8_stdio()
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="lcm", description="Generate and monitor long coding transcripts.")
    parser.add_argument("command", nargs="?", choices=["generate", "insert", "monitor"])
    parser.add_argument("--version", action="store_true")
    if not arguments or arguments[0] in {"--help", "-h", "--version"}:
        parsed = parser.parse_args(arguments)
        if parsed.version:
            try:
                print(version("long-context-monitoring"))
            except PackageNotFoundError:
                print("0.1.0")
        else:
            parser.print_help()
        return 0
    command = arguments[0]
    if command == "generate":
        from long_context_monitoring.generate_transcript.live import main as run
    elif command == "insert":
        from long_context_monitoring.insert import main as run
    elif command == "monitor":
        from long_context_monitoring.monitor.__main__ import main as run
    else:
        parser.error(f"unknown command {command!r}")
    return run(arguments[1:]) or 0


if __name__ == "__main__":
    raise SystemExit(main())
