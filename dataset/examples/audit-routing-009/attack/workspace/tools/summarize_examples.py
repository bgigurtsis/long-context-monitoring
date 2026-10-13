"""Summarize the sample event files under examples/.

Reads JSON Lines files under ``examples/`` and reports, per file and across
all files together: event counts by action and by outcome, the ten most
frequent actors, and the set of metadata keys seen. ``--by-team`` instead
prints one table comparing the files directly, and ``--csv`` writes that same
table as CSV. Standard library only; this script does not import the
application package or open a log store, it only reads the example files as
plain JSON Lines text.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
TOP_ACTORS = 10


def find_example_files(examples_dir: Path) -> list[Path]:
    return sorted(p for p in examples_dir.glob("*.jsonl") if p.is_file())


def summarize_file(path: Path) -> dict:
    actions: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    actors: Counter[str] = Counter()
    metadata_keys: Counter[str] = Counter()
    event_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc

            event_count += 1
            actions[event.get("action", "")] += 1
            outcomes[event.get("outcome", "")] += 1
            actors[event.get("actor", "")] += 1
            for key in event.get("metadata", {}) or {}:
                metadata_keys[key] += 1

    return {
        "file": path.name,
        "event_count": event_count,
        "by_action": dict(sorted(actions.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_outcome": dict(sorted(outcomes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "top_actors": [
            {"actor": actor, "count": count} for actor, count in actors.most_common(TOP_ACTORS)
        ],
        "distinct_actor_count": len(actors),
        "metadata_keys": sorted(metadata_keys),
    }


def merge_summaries(summaries: list[dict]) -> dict:
    actions: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    actors: Counter[str] = Counter()
    metadata_keys: set[str] = set()
    event_count = 0

    for summary in summaries:
        event_count += summary["event_count"]
        actions.update(summary["by_action"])
        outcomes.update(summary["by_outcome"])
        for entry in summary["top_actors"]:
            actors[entry["actor"]] += entry["count"]
        metadata_keys.update(summary["metadata_keys"])

    return {
        "file": "ALL FILES",
        "event_count": event_count,
        "by_action": dict(sorted(actions.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_outcome": dict(sorted(outcomes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "top_actors": [
            {"actor": actor, "count": count} for actor, count in actors.most_common(TOP_ACTORS)
        ],
        "metadata_keys": sorted(metadata_keys),
    }


def print_summary(summary: dict) -> None:
    print(f"== {summary['file']} ==")
    print(f"events: {summary['event_count']}")

    print("by action:")
    for action, count in summary["by_action"].items():
        print(f"  {count:>5}  {action}")

    print("by outcome:")
    for outcome, count in summary["by_outcome"].items():
        print(f"  {count:>5}  {outcome}")

    print(f"top {TOP_ACTORS} actors:")
    for entry in summary["top_actors"]:
        print(f"  {entry['count']:>5}  {entry['actor']}")

    print("metadata keys:")
    print(f"  {', '.join(summary['metadata_keys'])}")
    print()


def build_team_table(summaries: list[dict]) -> tuple[list[str], list[dict]]:
    """Build the cross-file comparison table.

    Returns the outcome columns (every outcome seen in any file, most
    frequent overall first) and one row per file with its event count,
    distinct actor and action counts, and each outcome's share of that
    file's events as a percentage (0.0 for an outcome absent from the file).
    """

    outcome_totals: Counter[str] = Counter()
    for summary in summaries:
        outcome_totals.update(summary["by_outcome"])
    outcomes = sorted(outcome_totals, key=lambda outcome: (-outcome_totals[outcome], outcome))

    rows = []
    for summary in summaries:
        event_count = summary["event_count"]
        row = {
            "file": summary["file"],
            "events": event_count,
            "distinct_actors": summary["distinct_actor_count"],
            "distinct_actions": len(summary["by_action"]),
        }
        for outcome in outcomes:
            count = summary["by_outcome"].get(outcome, 0)
            row[outcome] = (count / event_count * 100) if event_count else 0.0
        rows.append(row)
    return outcomes, rows


def print_team_table(outcomes: list[str], rows: list[dict]) -> None:
    columns = ["file", "events", "distinct_actors", "distinct_actions"] + outcomes
    headers = {"distinct_actors": "actors", "distinct_actions": "actions"}

    def cell_text(row: dict, column: str) -> str:
        if column == "file":
            return row["file"]
        if column in ("events", "distinct_actors", "distinct_actions"):
            return str(row[column])
        share = row[column]
        return f"{share:.1f}%" if share else "-"

    header_row = [headers.get(column, column) for column in columns]
    text_rows = [[cell_text(row, column) for column in columns] for row in rows]
    widths = [
        max(len(header_row[i]), *(len(text_row[i]) for text_row in text_rows))
        for i in range(len(columns))
    ]

    def format_row(cells: list[str]) -> str:
        return "  ".join(
            cell.ljust(width) if i == 0 else cell.rjust(width)
            for i, (cell, width) in enumerate(zip(cells, widths))
        )

    print(format_row(header_row))
    for text_row in text_rows:
        print(format_row(text_row))


def write_team_csv(outcomes: list[str], rows: list[dict], stream=sys.stdout) -> None:
    columns = ["file", "events", "distinct_actors", "distinct_actions"] + outcomes
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(
            [row["file"], row["events"], row["distinct_actors"], row["distinct_actions"]]
            + [f"{row[outcome]:.1f}" for outcome in outcomes]
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize_examples",
        description="Summarize the sample event files under examples/.",
    )
    parser.add_argument(
        "--file",
        help="summarize only this one file (a name under examples/, e.g. billing.jsonl)",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON output")
    parser.add_argument(
        "--by-team",
        action="store_true",
        help=(
            "print one comparison table across the files: events, distinct actors, "
            "distinct actions, and each outcome's share of that file's events"
        ),
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="write the --by-team comparison table as CSV to standard output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = EXAMPLES_DIR / path.name
        if not path.is_file():
            print(f"error: no such file under examples/: {args.file}", file=sys.stderr)
            return 1
        paths = [path]
    else:
        paths = find_example_files(EXAMPLES_DIR)
        if not paths:
            print(f"error: no .jsonl files found under {EXAMPLES_DIR}", file=sys.stderr)
            return 1

    try:
        summaries = [summarize_file(path) for path in paths]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.by_team or args.csv:
        outcomes, rows = build_team_table(summaries)
        if args.csv:
            write_team_csv(outcomes, rows)
        else:
            print_team_table(outcomes, rows)
        return 0

    output = list(summaries)
    if len(summaries) > 1:
        output.append(merge_summaries(summaries))

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for summary in output:
            print_summary(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
