"""Web application for visualizing attendance data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from flask import Flask, jsonify, redirect, render_template, request, url_for

from .parser import ParseError, parse_rows_from_text
from .report import build_matrix, collect_dates
from .storage import AttendanceStore, DEFAULT_STORAGE_FILE


def _sorted_profiles(store: AttendanceStore) -> List:
    """Return profiles sorted by name and email."""

    return sorted(store.profiles(), key=lambda profile: ((profile.name or "").lower(), profile.email))


def _attendance_summary(store: AttendanceStore) -> dict[str, object]:
    profiles = _sorted_profiles(store)
    dates = collect_dates(profiles)
    matrix = build_matrix(profiles)
    date_labels = [value.strftime("%Y-%m-%d") for value in dates]

    table_rows = []
    for profile in profiles:
        attendance_flags = [bool(matrix.get(profile.email, {}).get(date)) for date in dates]
        table_rows.append(
            {
                "name": profile.name or "(Unknown)",
                "email": profile.email,
                "flags": attendance_flags,
                "event_count": len(profile.events),
                "events": [
                    {
                        "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M"),
                        "source": event.source or "",
                    }
                    for event in profile.events
                ],
            }
        )

    counts = []
    for idx, date in enumerate(dates):
        attendees = sum(1 for profile_flags in matrix.values() if profile_flags.get(date))
        counts.append({"label": date_labels[idx], "count": attendees})

    return {
        "profiles": table_rows,
        "dates": date_labels,
        "counts": counts,
        "total_profiles": len(profiles),
    }


def create_app(store_path: Optional[Path] = None) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))

    initial_path = Path(store_path).expanduser() if store_path else DEFAULT_STORAGE_FILE
    current_store_path = initial_path.resolve()
    store = AttendanceStore(current_store_path)
    stores_directory = current_store_path.parent

    def normalize_path(path_value) -> Path:
        return Path(path_value).expanduser().resolve()

    def available_store_files() -> List[Path]:
        files: List[Path] = []
        if stores_directory.exists():
            for candidate in stores_directory.glob("*.json"):
                if candidate.is_file():
                    files.append(candidate.resolve())
        unique: List[Path] = []
        seen = set()
        for candidate in sorted(files, key=lambda item: item.name.lower()):
            if candidate not in seen:
                seen.add(candidate)
                unique.append(candidate)
        return unique

    def set_store_path(target: Path) -> Optional[str]:
        nonlocal store, current_store_path, stores_directory
        try:
            resolved = normalize_path(target)
        except OSError as exc:
            return f"Unable to resolve store path: {exc}"
        try:
            candidate = AttendanceStore(resolved)
        except json.JSONDecodeError as exc:
            return f"Store file contains invalid JSON: {exc}"
        except OSError as exc:
            return f"Unable to open store file: {exc}"
        store = candidate
        current_store_path = resolved
        stores_directory = current_store_path.parent
        return None

    def refresh_store() -> Optional[str]:
        if not store.path.exists():
            return None
        try:
            store.load()
        except json.JSONDecodeError as exc:
            return f"Unable to read store file: {exc}"
        except OSError as exc:
            return f"Unable to read store file: {exc}"
        return None

    def store_options() -> List[dict[str, str]]:
        options: List[dict[str, str]] = []
        seen = set()
        for candidate in available_store_files():
            seen.add(candidate)
            options.append({"label": candidate.name, "value": str(candidate)})
        if current_store_path not in seen:
            options.insert(0, {"label": current_store_path.name, "value": str(current_store_path)})
        return options

    def next_default_store_name() -> str:
        existing_names = {candidate.name for candidate in available_store_files()}
        existing_names.add(current_store_path.name)
        base_name = "attendance_data"
        suffix = ".json"
        if f"{base_name}{suffix}" not in existing_names:
            return f"{base_name}{suffix}"
        index = 2
        while True:
            candidate = f"{base_name}{index}{suffix}"
            if candidate not in existing_names:
                return candidate
            index += 1

    @app.route("/", methods=["GET"])
    def index() -> str:
        load_error = refresh_store()
        summary = _attendance_summary(store)
        status = request.args.get("status")
        message = request.args.get("message")
        if load_error and not status:
            status = "error"
            message = load_error
        return render_template(
            "index.html",
            summary=summary,
            status=status,
            message=message,
            current_store=str(current_store_path),
            current_store_name=current_store_path.name,
            store_directory=str(stores_directory),
            store_options=store_options(),
            suggested_store_name=next_default_store_name(),
        )

    @app.route("/import", methods=["POST"])
    def import_data():
        uploaded = request.files.get("file")
        label = request.form.get("source") or None

        if uploaded is None or uploaded.filename == "":
            return redirect(url_for("index", status="error", message="Select a file to import."))

        raw_bytes = uploaded.read()
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return redirect(url_for("index", status="error", message="Unable to decode uploaded file."))

        try:
            rows = parse_rows_from_text(text)
        except ParseError as exc:
            return redirect(url_for("index", status="error", message=str(exc)))

        imported = 0
        source_label = label or uploaded.filename
        for row in rows:
            store.record_attendance(row.name, row.email, row.timestamp, source=source_label)
            imported += 1

        if imported:
            store.save()
            feedback = f"Imported {imported} row(s)."
        else:
            feedback = "No new rows were imported."

        return redirect(url_for("index", status="success", message=feedback))

    @app.route("/store/create", methods=["POST"])
    def create_store_route():
        name = (request.form.get("store_name") or "").strip()
        if not name:
            return redirect(url_for("index", status="error", message="Provide a name for the store file."))
        if Path(name).name != name:
            return redirect(url_for("index", status="error", message="Provide a file name without directories."))
        if not name.lower().endswith(".json"):
            name += ".json"

        candidate_path = (stores_directory / name).expanduser().resolve()
        if candidate_path.exists():
            if not candidate_path.is_file():
                return redirect(url_for("index", status="error", message="A directory with that name already exists."))
            error_message = set_store_path(candidate_path)
            if error_message:
                return redirect(url_for("index", status="error", message=error_message))
            return redirect(url_for("index", status="success", message=f"Switched to existing store '{candidate_path.name}'."))

        try:
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text("{}\n", encoding="utf-8")
        except OSError as exc:
            return redirect(url_for("index", status="error", message=f"Unable to create store file: {exc}"))

        error_message = set_store_path(candidate_path)
        if error_message:
            return redirect(url_for("index", status="error", message=error_message))

        store.save()
        return redirect(url_for("index", status="success", message=f"Created store '{candidate_path.name}'."))

    @app.route("/store/select", methods=["POST"])
    def select_store_route():
        target_raw = (request.form.get("store_path") or "").strip()
        if not target_raw:
            return redirect(url_for("index", status="error", message="Select a store file from the list."))

        try:
            target_path = normalize_path(target_raw)
        except OSError as exc:
            return redirect(url_for("index", status="error", message=f"Unable to resolve selected store: {exc}"))

        allowed_paths = {current_store_path}
        for candidate in available_store_files():
            allowed_paths.add(candidate)

        if target_path not in allowed_paths:
            return redirect(url_for("index", status="error", message="Select a store file from the provided options."))
        if not target_path.exists():
            return redirect(url_for("index", status="error", message="Selected store file does not exist."))
        if not target_path.is_file():
            return redirect(url_for("index", status="error", message="Selected store is not a file."))

        error_message = set_store_path(target_path)
        if error_message:
            return redirect(url_for("index", status="error", message=error_message))

        return redirect(url_for("index", status="success", message=f"Switched to store '{target_path.name}'."))

    @app.route("/api/data", methods=["GET"])
    def api_data():
        refresh_store()
        summary = _attendance_summary(store)
        return jsonify(summary)

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the attendance visualization web app")
    parser.add_argument("--store", type=Path, default=None, help="Path to the attendance data store")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to serve on")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    args = parser.parse_args()
    app = create_app(args.store)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":  # pragma: no cover
    main()

