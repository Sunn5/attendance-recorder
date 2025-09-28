# Attendance Recorder

> Turn Microsoft Forms attendance exports into reusable, searchable records from the CLI or a lightweight web dashboard.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Command-Line Quick Start](#command-line-quick-start)
- [CLI Reference](#cli-reference)
- [Data Storage](#data-storage)
- [Web Dashboard](#web-dashboard)
- [Sample Workflow](#sample-workflow)
- [Development Notes](#development-notes)
- [License](#license)

## Overview

Attendance Recorder ingests CSV or TSV exports produced by Microsoft Forms and keeps track of who joined each session. Imports build a consolidated history per participant, which you can explore from the command line or in a small browser dashboard. All data lives in a single JSON file, making it easy to version, back up, or move between machines.

## Features

- Automatic parsing of Microsoft Forms exports with flexible header detection for time, name, and email columns.
- De-duplicated attendance history: repeated submissions for the same person and timestamp are ignored.
- CLI subcommands to list participants, inspect individual histories, render an attendance matrix, and export the raw JSON store.
- Optional `--store` flag to work with multiple datasets or keep separate histories per team.
- Lightweight Flask dashboard that lets you upload new exports, browse an interactive matrix, review per-person details, and view attendance trends via Chart.js.
- Included sample data (`examples/sample_attendance.csv`) to test the workflow without real submissions.
- Ships without external dependencies for the CLI; only Flask is required when you want to run the dashboard.

## Requirements

- Python 3.10 or newer.
- Windows, macOS, or Linux.
- Optional: Flask (install with `pip install flask`) if you plan to use the web dashboard.
- Optional: a virtual environment (`python -m venv .venv`) to keep project dependencies isolated.

## Installation

```bash
git clone <repository-url>
cd attendance-recorder
python -m venv .venv           # optional but recommended
source .venv/bin/activate      # use .\.venv\Scripts\activate on Windows
pip install --upgrade pip
pip install flask              # only if you plan to use the dashboard
```

The CLI runs directly from the repository; there is no packaging step required. Skip the Flask install if you only need the command line tools.

## Command-Line Quick Start

Run the module to see the available commands:

```bash
python -m attendance_recorder --help
```

Try the full flow with the bundled sample file:

```bash
python -m attendance_recorder import examples/sample_attendance.csv --source "Weekly stand-up"
python -m attendance_recorder profiles
python -m attendance_recorder history alex@example.com
python -m attendance_recorder table
python -m attendance_recorder export --output exported.json
```

By default, the data is written to `attendance_data.json` in the current directory. Use `--store path/to/file.json` on any command to point to a different dataset.

## CLI Reference

- `import <file> [--source LABEL]`: Load a CSV/TSV export. Each row becomes an attendance event, optionally labeled with the source string (meeting name, etc.).
- `profiles`: Show every participant along with the number of sessions they have attended.
- `history <email>`: List the timestamped events for a single participant.
- `table`: Render an ASCII matrix of participants versus session dates.
- `export [--output <file>]`: Dump the JSON store to stdout or to the specified file.

Global options:

- `--store <path>`: Override the location of the JSON store. Useful for keeping separate histories (for example, `--store data/training.json`).
- `--help`: Display help for the main command or any subcommand.

## Data Storage

Attendance Recorder writes a single JSON document that is easy to inspect or commit to source control. The top-level keys are lower-cased email addresses:

```json
{
  "alex@example.com": {
    "name": "Alex Doe",
    "email": "alex@example.com",
    "events": [
      {
        "timestamp": "2024-03-01T09:05:00",
        "source": "Weekly stand-up"
      }
    ]
  }
}
```

- Dates are stored in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`).
- Duplicate events (same participant + timestamp) are filtered out automatically.
- Column names are matched case-insensitively; common synonyms such as "Submission Time" or "Email Address" are supported. Missing required columns raise a clear parsing error.

You can safely edit the JSON file by hand, but remember to keep the ISO timestamp format if you do.

## Web Dashboard

The web interface offers a friendlier way to explore the same dataset.

1. Install Flask if you have not already: `pip install flask`.
2. Configure HTTP Basic Auth credentials. The dashboard refuses to start unless both variables are set:
   ```bash
   export ATTENDANCE_AUTH_USERNAME="admin"
   export ATTENDANCE_AUTH_PASSWORD="change-me"
   ```
   On Windows (PowerShell):
   ```powershell
   $Env:ATTENDANCE_AUTH_USERNAME = "admin"
   $Env:ATTENDANCE_AUTH_PASSWORD = "change-me"
   ```
   Choose a strong password and keep it secret—every endpoint requires these credentials.
3. Start the server from the repository root:
   ```bash
   python -m attendance_recorder.webapp --store attendance_data.json --host 127.0.0.1 --port 5000
   ```
   On Windows you can also run `start-attendance-dashboard.bat`, which launches the server and opens your browser automatically.
4. Visit http://127.0.0.1:5000. Your browser will prompt for the username and password you configured. Use the upload form to merge new CSV/TSV exports, see attendance trends, and inspect per-person timelines.

Useful endpoints:

- `/`: Dashboard UI with charts, table, and detailed lists.
- `/import`: POST endpoint used by the upload form to add new data.
- `/api/data`: Returns the aggregated attendance summary as JSON; handy for building your own visualizations.

### Authentication and deployment tips

- All dashboard routes (`/`, `/import`, `/api/data`) require HTTP Basic Auth using `ATTENDANCE_AUTH_USERNAME` and `ATTENDANCE_AUTH_PASSWORD`. Requests without valid credentials receive `401 Unauthorized` responses.
- Command-line uploads with `curl` or similar tools can pass credentials via `-u "$ATTENDANCE_AUTH_USERNAME:$ATTENDANCE_AUTH_PASSWORD"`.
- Bind the server to `127.0.0.1` (the default) and access it through an SSH tunnel or reverse proxy that can add TLS if you need remote access. Avoid exposing the Flask development server directly to the public internet.

The dashboard reads the same JSON store that the CLI manages, so you can alternate between the two without extra synchronization steps.

## Sample Workflow

1. Create or locate the directory where you want to keep the store.
2. Import a new Microsoft Forms export:
   ```bash
   python -m attendance_recorder import /path/to/forms-export.csv --store data/team.json --source "Sprint Review"
   ```
3. Review attendance:
   ```bash
   python -m attendance_recorder table --store data/team.json
   ```
4. Share the data:
   ```bash
   python -m attendance_recorder export --store data/team.json --output reports/team-export.json
   ```
5. (Optional) Start the dashboard to present the results during a meeting.

## Development Notes

- Source code lives under `attendance_recorder/`. Key modules:
  - `parser.py` for CSV parsing and header detection.
  - `storage.py` for the JSON-backed data store.
  - `report.py` for the ASCII table used by the `table` command.
  - `webapp.py` for the Flask dashboard (templates in `attendance_recorder/templates/`).
- Example data resides in `examples/`.
- There is currently no automated test suite; manual verification typically involves importing the sample data and spot-checking the CLI outputs.
- The project is intentionally dependency-light so you can embed it in existing automation scripts or extend it with minimal effort.

## License

Attendance Recorder is released under the [MIT License](LICENSE).
