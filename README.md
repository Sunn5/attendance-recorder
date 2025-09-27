# attendance-recorder

`attendance-recorder` is a small command line utility that helps you organise
attendance tables exported from Microsoft Forms.  You can import the table that
you copied or downloaded from Forms (containing time, name, and e‑mail columns)
and the tool will build a profile for each person, keeping track of every
session they attended.  Once the data is imported you can list all profiles,
inspect a person's attendance history, or display a matrix showing who attended
each date.

## Getting started

The command line workflow has no external dependencies beyond Python 3.10+.  The optional web dashboard depends on Flask (install with `pip install flask`).  You can run it
directly from the repository:

```bash
python -m attendance_recorder --help
```

### Import attendance from Microsoft Forms

Save your Microsoft Forms attendance table as a CSV/TSV file (you can also copy
the table into a text file).  Then import it using the `import` command.  By
default the data is stored in `attendance_data.json` in the current directory.

```bash
python -m attendance_recorder import examples/sample_attendance.csv --source "Weekly stand-up"
```

Each row is mapped to a participant profile using their e‑mail address.  The
timestamp is converted into an attendance event so you can review their
history later.

### Review the stored data

List all recorded profiles and see how many sessions each person has attended:

```bash
python -m attendance_recorder profiles
```

Show a person's attendance history:

```bash
python -m attendance_recorder history alex@example.com
```

Display a name/date table to quickly check who attended a session on each day:

```bash
python -m attendance_recorder table
```

Export the raw JSON data (useful for backups or feeding other tools):

```bash
python -m attendance_recorder export --output exported.json
```

### Sample data

A small sample export is included in `examples/sample_attendance.csv` so you can
test the workflow without connecting to Microsoft Forms.

### Visualise attendance in the browser

You can launch a lightweight web dashboard to explore the stored data.

1. Install Flask (once): `pip install flask`
2. Ensure your `attendance_data.json` is up to date (import with the CLI if needed).
3. Start the server from the repository root:
   ```bash
   python -m attendance_recorder.webapp --store attendance_data.json --host 127.0.0.1 --port 5000
   ```
4. Visit http://127.0.0.1:5000 in your browser. Upload additional CSV/TSV exports to merge them and refresh the charts.

Use `Ctrl+C` in the terminal to stop the server.

