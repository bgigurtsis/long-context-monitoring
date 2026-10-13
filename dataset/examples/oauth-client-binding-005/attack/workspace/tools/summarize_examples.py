"""Read-only summary tool for the sample listings under examples/.

Reads the JSON Lines files under examples/ and prints, for each file and for
all files combined: listing counts by category, by status, and by launch
year, plus the ten owning teams with the most listings.

--by-group prints one comparison table across the summarized files instead
(listings, distinct owning teams, distinct categories, beta share); --csv
prints that same table as CSV.

Standard library only. Reads only files under examples/ (matched by
--file or, by default, every "*.jsonl" file there); it does not import the
oauthsvc package or open any database.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

TOP_TEAMS_LIMIT = 10


def load_listings(path: Path) -> list[dict[str, Any]]:
    listings = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                listings.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}: invalid JSON on line {line_no}: {exc}") from exc
    return listings


def summarize(listings: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_launch_year: Counter[str] = Counter()
    by_team: Counter[str] = Counter()

    for listing in listings:
        by_category[listing.get("category", "unknown")] += 1
        by_status[listing.get("status", "unknown")] += 1
        launch_date = listing.get("launch_date", "")
        year = launch_date.split("-")[0] if launch_date else "unknown"
        by_launch_year[year] += 1
        by_team[listing.get("owning_team", "unknown")] += 1

    return {
        "total_listings": len(listings),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_status": dict(sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_launch_year": dict(sorted(by_launch_year.items(), key=lambda kv: kv[0])),
        "top_owning_teams": [
            {"owning_team": team, "count": count}
            for team, count in by_team.most_common(TOP_TEAMS_LIMIT)
        ],
    }


def print_summary(title: str, summary: dict[str, Any]) -> None:
    print(f"== {title} ==")
    print(f"Total listings: {summary['total_listings']}")

    print("By category:")
    for category, count in summary["by_category"].items():
        print(f"  {category}: {count}")

    print("By status:")
    for status, count in summary["by_status"].items():
        print(f"  {status}: {count}")

    print("By launch year:")
    for year, count in summary["by_launch_year"].items():
        print(f"  {year}: {count}")

    print(f"Top {TOP_TEAMS_LIMIT} owning teams:")
    for entry in summary["top_owning_teams"]:
        print(f"  {entry['owning_team']}: {entry['count']}")

    print()


def merge_counters(summaries: list[dict[str, Any]], key: str) -> Counter:
    merged: Counter = Counter()
    for summary in summaries:
        merged.update(summary[key])
    return merged


def combine(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(s["total_listings"] for s in summaries)
    by_category = merge_counters(summaries, "by_category")
    by_status = merge_counters(summaries, "by_status")
    by_launch_year = merge_counters(summaries, "by_launch_year")

    by_team: Counter[str] = Counter()
    for summary in summaries:
        for entry in summary["top_owning_teams"]:
            by_team[entry["owning_team"]] += entry["count"]

    return {
        "total_listings": total,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_status": dict(sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_launch_year": dict(sorted(by_launch_year.items(), key=lambda kv: kv[0])),
        "top_owning_teams": [
            {"owning_team": team, "count": count}
            for team, count in by_team.most_common(TOP_TEAMS_LIMIT)
        ],
    }


def group_row(name: str, listings: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(listings)
    distinct_teams = len({listing.get("owning_team", "unknown") for listing in listings})
    distinct_categories = len({listing.get("category", "unknown") for listing in listings})
    beta_count = sum(1 for listing in listings if listing.get("status") == "beta")
    beta_share_percent = round((beta_count / total * 100) if total else 0.0, 1)

    return {
        "file": name,
        "listings": total,
        "distinct_owning_teams": distinct_teams,
        "distinct_categories": distinct_categories,
        "beta_share_percent": beta_share_percent,
    }


GROUP_COLUMNS = ["file", "listings", "distinct_owning_teams", "distinct_categories", "beta_share_percent"]


def print_group_table(rows: list[dict[str, Any]]) -> None:
    widths = {
        "file": max(len("file"), max((len(row["file"]) for row in rows), default=0)),
        "listings": max(len("listings"), 8),
        "distinct_owning_teams": max(len("distinct_owning_teams"), 8),
        "distinct_categories": max(len("distinct_categories"), 8),
        "beta_share_percent": max(len("beta_share_percent"), 8),
    }

    header = (
        f"{'file':<{widths['file']}}  {'listings':>{widths['listings']}}  "
        f"{'distinct_owning_teams':>{widths['distinct_owning_teams']}}  "
        f"{'distinct_categories':>{widths['distinct_categories']}}  "
        f"{'beta_share_percent':>{widths['beta_share_percent']}}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['file']:<{widths['file']}}  "
            f"{row['listings']:>{widths['listings']}}  "
            f"{row['distinct_owning_teams']:>{widths['distinct_owning_teams']}}  "
            f"{row['distinct_categories']:>{widths['distinct_categories']}}  "
            f"{row['beta_share_percent']:>{widths['beta_share_percent']-1}.1f}%"
        )


def write_group_csv(rows: list[dict[str, Any]]) -> None:
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(GROUP_COLUMNS)
    for row in rows:
        writer.writerow([row[column] for column in GROUP_COLUMNS])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the sample application listings under examples/."
    )
    parser.add_argument(
        "--file",
        help="Summarize only this one file (name or path under examples/), "
        "instead of every *.jsonl file there.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of formatted text.",
    )
    parser.add_argument(
        "--by-group",
        action="store_true",
        help="Print one comparison table across the summarized files: listings, "
        "distinct owning teams, distinct categories, and beta share per file. "
        "Takes precedence over --json.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Print the --by-group comparison table as CSV instead of formatted "
        "text. Implies --by-group.",
    )
    return parser.parse_args(argv)


def resolve_files(file_arg: str | None) -> list[Path]:
    if file_arg is None:
        return sorted(EXAMPLES_DIR.glob("*.jsonl"))

    candidate = Path(file_arg)
    path = candidate if candidate.is_absolute() else EXAMPLES_DIR / candidate.name
    if not path.is_file():
        raise SystemExit(f"error: no such file under examples/: {file_arg}")
    return [path]


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        files = resolve_files(args.file)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1

    if not files:
        print("error: no *.jsonl files found under examples/", file=sys.stderr)
        return 1

    per_file: list[tuple[str, dict[str, Any]]] = []
    per_file_listings: list[tuple[str, list[dict[str, Any]]]] = []
    for path in files:
        try:
            listings = load_listings(path)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        per_file_listings.append((path.name, listings))
        per_file.append((path.name, summarize(listings)))

    if args.by_group or args.csv:
        rows = [group_row(name, listings) for name, listings in per_file_listings]
        if args.csv:
            write_group_csv(rows)
        else:
            print_group_table(rows)
        return 0

    if args.json:
        output: dict[str, Any] = {"files": {name: summary for name, summary in per_file}}
        if len(per_file) > 1:
            output["combined"] = combine([summary for _, summary in per_file])
        print(json.dumps(output, indent=2))
        return 0

    for name, summary in per_file:
        print_summary(name, summary)

    if len(per_file) > 1:
        print_summary("all files combined", combine([summary for _, summary in per_file]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
