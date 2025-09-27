"""Utilities for loading and saving attendance data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_STORAGE_FILE = Path("attendance_data.json")


@dataclass
class AttendanceEvent:
    """Represents a single attendance event for a participant."""

    timestamp: datetime
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        data = {"timestamp": self.timestamp.strftime(ISO_FORMAT)}
        if self.source:
            data["source"] = self.source
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "AttendanceEvent":
        timestamp = datetime.strptime(data["timestamp"], ISO_FORMAT)
        source = data.get("source")
        return cls(timestamp=timestamp, source=source)


@dataclass
class PersonProfile:
    """Stores the attendance history for an individual participant."""

    name: str
    email: str
    events: List[AttendanceEvent] = field(default_factory=list)

    def register_event(self, event: AttendanceEvent) -> None:
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "email": self.email,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PersonProfile":
        events = [AttendanceEvent.from_dict(e) for e in data.get("events", [])]
        return cls(name=data["name"], email=data["email"], events=events)


class AttendanceStore:
    """Persisted storage for attendance profiles."""

    def __init__(self, path: Path = DEFAULT_STORAGE_FILE) -> None:
        self.path = Path(path)
        self._profiles: Dict[str, PersonProfile] = {}
        if self.path.exists():
            self.load()

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        profiles: Dict[str, PersonProfile] = {}
        for email, payload in data.items():
            profiles[email] = PersonProfile.from_dict(payload)
        self._profiles = profiles

    def save(self) -> None:
        payload = {email: profile.to_dict() for email, profile in self._profiles.items()}
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        self.path.write_text(text, encoding="utf-8")

    def profiles(self) -> Iterable[PersonProfile]:
        return self._profiles.values()

    def get_or_create(self, name: str, email: str) -> PersonProfile:
        profile = self._profiles.get(email.lower())
        if profile is None:
            profile = PersonProfile(name=name, email=email)
            self._profiles[email.lower()] = profile
        else:
            if profile.name != name:
                # Keep the earliest non-empty name.
                if profile.name.strip():
                    if name.strip() and profile.name.strip().lower() != name.strip().lower():
                        profile.name = name
                else:
                    profile.name = name
        return profile

    def record_attendance(self, name: str, email: str, timestamp: datetime, source: Optional[str] = None) -> None:
        profile = self.get_or_create(name=name, email=email)
        event = AttendanceEvent(timestamp=timestamp, source=source)
        if event.timestamp not in [e.timestamp for e in profile.events]:
            profile.register_event(event)

    def as_dict(self) -> Dict[str, Dict[str, object]]:
        return {email: profile.to_dict() for email, profile in self._profiles.items()}


def ensure_store(path: Optional[str]) -> AttendanceStore:
    if path:
        return AttendanceStore(Path(path))
    return AttendanceStore()
