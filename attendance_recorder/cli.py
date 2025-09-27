"""Command line interface for managing attendance data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from . import parser, report
from .storage import AttendanceStore


def build_parser() -> argparse.ArgumentParser:
    parser_obj = argparse.ArgumentParser(description="Organize Microsoft Forms attendance exports")
    parser_obj.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Path to the attendance data store (defaults to attendance_data.json)",
    )

    subparsers = parser_obj.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import a CSV/TSV export from Microsoft Forms")
    import_parser.add_argument("file", type=Path, help="Path to the exported table")
    import_parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Label to store with the imported data (e.g., meeting name)",
    )

    subparsers.add_parser("profiles", help="List the recorded profiles")
    subparsers.add_parser("table", help="Display a name/date attendance table")

    history_parser = subparsers.add_parser("history", help="Show attendance history for a single person")
    history_parser.add_argument("email", type=str, help="Email address of the person")

    export_parser = subparsers.add_parser("export", help="Export the current data as JSON")
    export_parser.add_argument("--output", type=Path, default=None, help="Output file path")

    return parser_obj


def cmd_import(store: AttendanceStore, args: argparse.Namespace) -> str:
    rows = parser.read_rows(args.file)
    for row in rows:
        store.record_attendance(row.name, row.email, row.timestamp, source=args.source)
    store.save()
    return f"Imported {len(rows)} rows from {args.file}"


def cmd_profiles(store: AttendanceStore) -> str:
    profiles = list(store.profiles())
    if not profiles:
        return "No profiles recorded yet."
    lines = []
    for profile in sorted(profiles, key=lambda p: (p.name.lower(), p.email)):
        lines.append(f"{profile.name} <{profile.email}> — {len(profile.events)} event(s)")
    return "\n".join(lines)


def cmd_table(store: AttendanceStore) -> str:
    profiles = list(store.profiles())
    return report.format_attendance_table(profiles)


def cmd_history(store: AttendanceStore, email: str) -> str:
    email = email.lower()
    profile = next((p for p in store.profiles() if p.email.lower() == email), None)
    if profile is None:
        return f"No attendance data found for {email}"
    lines = [f"Attendance history for {profile.name} <{profile.email}>:"]
    for event in profile.events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        suffix = f" ({event.source})" if event.source else ""
        lines.append(f"  • {timestamp}{suffix}")
    return "\n".join(lines)


def cmd_export(store: AttendanceStore, output: Optional[Path]) -> str:
    data = store.as_dict()
    json_text = json.dumps(data, indent=2, ensure_ascii=False)
    if output is None:
        return json_text
    output.write_text(json_text, encoding="utf-8")
    return f"Exported data to {output}"


def main(argv: Optional[list[str]] = None) -> str:
    parser_obj = build_parser()
    args = parser_obj.parse_args(argv)

    store = AttendanceStore(args.store) if args.store else AttendanceStore()

    if args.command == "import":
        return cmd_import(store, args)
    if args.command == "profiles":
        return cmd_profiles(store)
    if args.command == "table":
        return cmd_table(store)
    if args.command == "history":
        return cmd_history(store, args.email)
    if args.command == "export":
        return cmd_export(store, args.output)

    raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    print(main())
