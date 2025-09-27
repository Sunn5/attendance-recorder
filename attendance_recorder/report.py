"""Reporting utilities to summarize attendance."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Sequence

from .storage import PersonProfile


def collect_dates(profiles: Iterable[PersonProfile]) -> List[date]:
    """Return sorted unique dates for all attendance events."""

    seen = set()
    dates = []
    for profile in profiles:
        for event in profile.events:
            date = event.timestamp.date()
            if date not in seen:
                seen.add(date)
                dates.append(date)
    return sorted(dates)


def build_matrix(profiles: Iterable[PersonProfile]) -> Dict[str, Dict[date, bool]]:
    """Build a person/date matrix indicating attendance."""

    matrix: Dict[str, Dict[date, bool]] = defaultdict(dict)
    for profile in profiles:
        for event in profile.events:
            matrix[profile.email][event.timestamp.date()] = True
    return matrix


def format_attendance_table(profiles: Sequence[PersonProfile]) -> str:
    """Return a human friendly attendance matrix as a table."""

    profiles = sorted(profiles, key=lambda p: (p.name.lower(), p.email))
    dates = collect_dates(profiles)
    matrix = build_matrix(profiles)

    if not profiles:
        return "No attendance data available."

    date_headers = [date.strftime("%Y-%m-%d") for date in dates]

    header = ["Name", "Email", *date_headers]
    rows: List[List[str]] = [header]

    for profile in profiles:
        row = [profile.name or "(Unknown)", profile.email]
        for date in dates:
            row.append("✓" if matrix.get(profile.email, {}).get(date) else "")
        rows.append(row)

    # Determine column widths
    widths = [max(len(row[idx]) for row in rows) for idx in range(len(header))]

    def format_row(row: Sequence[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row))

    divider = "-+-".join("-" * width for width in widths)

    formatted_rows = [format_row(rows[0]), divider]
    formatted_rows.extend(format_row(row) for row in rows[1:])
    return "\n".join(formatted_rows)
