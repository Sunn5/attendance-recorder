"""Web application for visualizing attendance data."""

from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import List, Optional

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from .parser import ParseError, parse_rows_from_text
from .report import build_matrix, collect_dates
from .storage import AttendanceStore


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

    username = os.environ.get("ATTENDANCE_AUTH_USERNAME")
    password = os.environ.get("ATTENDANCE_AUTH_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "ATTENDANCE_AUTH_USERNAME and ATTENDANCE_AUTH_PASSWORD must be set to start the web app."
        )

    credentials = (username, password)
    app.config["AUTH_CREDENTIALS"] = credentials

    path = Path(store_path) if store_path else None
    store = AttendanceStore(path) if path else AttendanceStore()

    def refresh_store() -> None:
        if store.path and store.path.exists():
            store.load()

    def ensure_authorized() -> Optional[Response]:
        auth = request.authorization
        auth_type = (auth.type or "").lower() if auth else ""
        if auth and auth_type == "basic":
            if hmac.compare_digest(auth.username or "", credentials[0]) and hmac.compare_digest(
                auth.password or "", credentials[1]
            ):
                return None

        response = Response("Authentication required", 401)
        response.headers["WWW-Authenticate"] = 'Basic realm="Attendance Recorder"'
        return response

    @app.route("/", methods=["GET"])
    def index() -> Response | str:
        unauthorized = ensure_authorized()
        if unauthorized:
            return unauthorized
        refresh_store()
        summary = _attendance_summary(store)
        status = request.args.get("status")
        message = request.args.get("message")
        return render_template("index.html", summary=summary, status=status, message=message)

    @app.route("/import", methods=["POST"])
    def import_data() -> Response:
        unauthorized = ensure_authorized()
        if unauthorized:
            return unauthorized
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

    @app.route("/api/data", methods=["GET"])
    def api_data() -> Response:
        unauthorized = ensure_authorized()
        if unauthorized:
            return unauthorized
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

