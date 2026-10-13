#!/usr/bin/env python3
"""Read-only summary of the sample display-preference records under examples/.

Reads the JSON Lines files under examples/ (one JSON object per line) and
prints record counts by locale, time zone, theme, and text size, plus the
most common date formats, for each file and for all files combined.

Standard library only. Reads files under examples/ only; never imports the
accountsvc package and never opens a database.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

FIELDS = ("locale", "time_zone", "theme", "text_size")
DATE_FORMAT_FIELD = "date_format"
TOP_DATE_FORMATS = 5


class FileSummary:
    def __init__(self, name: str):
        self.name = name
        self.record_count = 0
        self.malformed_lines = 0
        self.counters = {field: Counter() for field in FIELDS}
        self.date_formats: Counter = Counter()

    def add(self, record: dict) -> None:
        self.record_count += 1
        for field in FIELDS:
            value = record.get(field)
            if value is not None:
                self.counters[field][value] += 1
        date_format = record.get(DATE_FORMAT_FIELD)
        if date_format is not None:
            self.date_formats[date_format] += 1

    def merge_into(self, other: "FileSummary") -> None:
        other.record_count += self.record_count
        other.malformed_lines += self.malformed_lines
        for field in FIELDS:
            other.counters[field].update(self.counters[field])
        other.date_formats.update(self.date_formats)

    def to_dict(self) -> dict:
        return {
            "record_count": self.record_count,
            "malformed_lines": self.malformed_lines,
            **{f"by_{field}": dict(self.counters[field].most_common()) for field in FIELDS},
            "most_common_date_formats": self.date_formats.most_common(TOP_DATE_FORMATS),
        }


def read_jsonl(path: Path) -> tuple[list[dict], int]:
    records = []
    malformed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(obj, dict):
                records.append(obj)
            else:
                malformed += 1
    return records, malformed


def summarize_file(path: Path) -> FileSummary:
    summary = FileSummary(path.name)
    records, malformed = read_jsonl(path)
    summary.malformed_lines = malformed
    for record in records:
        summary.add(record)
    return summary


def discover_files(examples_dir: Path) -> list[Path]:
    return sorted(examples_dir.glob("*.jsonl"))


def combine(summaries: Iterable[FileSummary]) -> FileSummary:
    combined = FileSummary("ALL FILES")
    for summary in summaries:
        summary.merge_into(combined)
    return combined


def format_counter_block(title: str, counter: Counter) -> list[str]:
    lines = [f"{title}:"]
    if not counter:
        lines.append("  (none)")
        return lines
    for value, count in counter.most_common():
        lines.append(f"  {value}: {count}")
    return lines


def format_text(name: str, summary: FileSummary) -> str:
    lines = [f"== {name} ==", f"records: {summary.record_count}"]
    if summary.malformed_lines:
        lines.append(f"malformed lines skipped: {summary.malformed_lines}")
    for field in FIELDS:
        lines.extend(format_counter_block(field, summary.counters[field]))
    lines.append("most common date formats:")
    if not summary.date_formats:
        lines.append("  (none)")
    else:
        for rank, (value, count) in enumerate(summary.date_formats.most_common(TOP_DATE_FORMATS), start=1):
            lines.append(f"  {rank}. {value}: {count}")
    return "\n".join(lines)


def region_row(summary: FileSummary) -> dict:
    dark_count = summary.counters["theme"].get("dark", 0)
    dark_share = (dark_count / summary.record_count) if summary.record_count else 0.0
    return {
        "file": summary.name,
        "records": summary.record_count,
        "distinct_locales": len(summary.counters["locale"]),
        "distinct_time_zones": len(summary.counters["time_zone"]),
        "dark_theme_pct": f"{dark_share * 100:.1f}%",
    }


def build_region_table(summaries: Iterable[FileSummary]) -> list[dict]:
    return [region_row(summary) for summary in summaries]


REGION_COLUMNS = ("file", "records", "distinct_locales", "distinct_time_zones", "dark_theme_pct")


def format_region_table_text(rows: list[dict]) -> str:
    widths = {col: max(len(col), *(len(str(row[col])) for row in rows)) if rows else len(col) for col in REGION_COLUMNS}
    header = "  ".join(col.ljust(widths[col]) for col in REGION_COLUMNS)
    lines = [header, "  ".join("-" * widths[col] for col in REGION_COLUMNS)]
    for row in rows:
        lines.append("  ".join(str(row[col]).ljust(widths[col]) for col in REGION_COLUMNS))
    return "\n".join(lines)


def format_region_table_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REGION_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def resolve_target_file(examples_dir: Path, file_arg: str) -> Path:
    candidate = Path(file_arg)
    if candidate.is_file():
        return candidate
    candidate = examples_dir / file_arg
    if candidate.is_file():
        return candidate
    candidate = examples_dir / f"{file_arg}.jsonl"
    if candidate.is_file():
        return candidate
    raise SystemExit(f"error: no such examples file: {file_arg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--examples-dir",
        default="examples",
        help="directory containing the .jsonl sample files (default: examples)",
    )
    parser.add_argument(
        "--file",
        help="summarize a single file (by name, e.g. nordics or nordics.jsonl) instead of all files",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON instead of text")
    parser.add_argument(
        "--by-region",
        action="store_true",
        help="print one comparison table across all sample files (records, distinct locales, "
        "distinct time zones, dark-theme share) instead of the per-file breakdown",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="write the --by-region comparison table as CSV to standard output",
    )
    args = parser.parse_args(argv)

    examples_dir = Path(args.examples_dir)

    if args.by_region or args.csv:
        if not examples_dir.is_dir():
            raise SystemExit(f"error: no such directory: {examples_dir}")
        files = discover_files(examples_dir)
        if not files:
            raise SystemExit(f"error: no .jsonl files found under {examples_dir}")
        rows = build_region_table(summarize_file(path) for path in files)
        if args.csv:
            print(format_region_table_csv(rows), end="")
        else:
            print(format_region_table_text(rows))
        return 0

    if args.file:
        target = resolve_target_file(examples_dir, args.file)
        summary = summarize_file(target)
        if args.json:
            print(json.dumps({"files": {summary.name: summary.to_dict()}}, indent=2, sort_keys=False))
        else:
            print(format_text(summary.name, summary))
        return 0

    if not examples_dir.is_dir():
        raise SystemExit(f"error: no such directory: {examples_dir}")

    files = discover_files(examples_dir)
    if not files:
        raise SystemExit(f"error: no .jsonl files found under {examples_dir}")

    summaries = [summarize_file(path) for path in files]
    combined = combine(summaries)

    if args.json:
        payload = {
            "files": {summary.name: summary.to_dict() for summary in summaries},
            "combined": combined.to_dict(),
        }
        print(json.dumps(payload, indent=2, sort_keys=False))
        return 0

    blocks = [format_text(summary.name, summary) for summary in summaries]
    blocks.append(format_text(f"ALL FILES ({len(files)} files)", combined))
    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
