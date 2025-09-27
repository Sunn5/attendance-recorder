"""Parsing utilities for Microsoft Forms attendance exports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Iterable, List, Optional

KNOWN_TIME_FIELDS = {
    "timestamp",
    "submission time",
    "start time",
    "date",
    "time",
}

KNOWN_NAME_FIELDS = {
    "name",
    "full name",
    "first name",
}

KNOWN_EMAIL_FIELDS = {
    "email",
    "email address",
    "user email",
}


@dataclass
class ParsedRow:
    """Represents a normalized row of attendance data."""

    timestamp: datetime
    name: str
    email: str


class ParseError(RuntimeError):
    """Raised when the file cannot be parsed."""


def sniff_delimiter(sample: str) -> str:
    """Guess the delimiter used in the imported table."""

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",\t;")
        return dialect.delimiter
    except csv.Error:
        return ","


def _detect_column(headers: List[str], known_names: Iterable[str]) -> Optional[int]:
    lower_headers = [header.strip().lower() for header in headers]
    known = [name.lower() for name in known_names]
    for idx, header in enumerate(lower_headers):
        if header in known:
            return idx
    return None


def parse_datetime(value: str) -> datetime:
    """Parse a datetime string from Microsoft Forms exports."""

    value = value.strip()
    if not value:
        raise ParseError("Empty timestamp value")

    formats = [
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ParseError(f"Unable to parse timestamp '{value}'")


def parse_rows_from_text(text: str) -> List[ParsedRow]:
    """Parse attendance rows from a text payload."""

    sample = text[:1024]
    delimiter = sniff_delimiter(sample) if sample else ","

    reader = csv.reader(StringIO(text), delimiter=delimiter)
    try:
        headers = next(reader)
    except StopIteration as exc:  # pragma: no cover - empty file guard
        raise ParseError("The provided file is empty") from exc

    time_idx = _detect_column(headers, KNOWN_TIME_FIELDS)
    name_idx = _detect_column(headers, KNOWN_NAME_FIELDS)
    email_idx = _detect_column(headers, KNOWN_EMAIL_FIELDS)

    if time_idx is None or name_idx is None or email_idx is None:
        raise ParseError(
            "Could not detect required columns. Ensure the file contains time, name, and email headers."
        )

    rows: List[ParsedRow] = []
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        timestamp = parse_datetime(row[time_idx])
        name = row[name_idx].strip()
        email = row[email_idx].strip().lower()
        if not name or not email:
            continue
        rows.append(ParsedRow(timestamp=timestamp, name=name, email=email))

    return rows


def read_rows(path: Path) -> List[ParsedRow]:
    """Read attendance rows from a CSV/TSV file."""

    text = path.read_text(encoding="utf-8-sig")
    return parse_rows_from_text(text)
