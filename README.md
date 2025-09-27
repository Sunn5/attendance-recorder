# attendance-recorder

`attendance-recorder` is a small command line utility that helps you organise
attendance tables exported from Microsoft Forms.  You can import the table that
you copied or downloaded from Forms (containing time, name, and e‑mail columns)
and the tool will build a profile for each person, keeping track of every
session they attended.  Once the data is imported you can list all profiles,
inspect a person's attendance history, or display a matrix showing who attended
each date.

## Getting started

The project has no external dependencies beyond Python 3.10+.  You can run it
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
