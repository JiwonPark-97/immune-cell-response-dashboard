"""
Create a fresh SQLite database from supplied cell-count dataset.
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "immune-cells.db"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    project_code TEXT NOT NULL UNIQUE
);

CREATE TABLE subjects (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    subject_code TEXT NOT NULL UNIQUE,
    condition TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
    treatment TEXT NOT NULL,
    response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL)
);

CREATE TABLE samples (
    id INTEGER PRIMARY KEY,
    sample_code TEXT NOT NULL UNIQUE,
    sample_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    time_from_treatment_start INTEGER NOT NULL
);

CREATE TABLE cell_populations (
    id INTEGER PRIMARY KEY,
    population_name TEXT NOT NULL UNIQUE
);

CREATE TABLE cell_counts (
    sample_id INTEGER NOT NULL REFERENCES samples(id),
    population_id INTEGER NOT NULL REFERENCES cell_populations(id),
    cell_count INTEGER NOT NULL CHECK (cell_count >= 0),
    PRIMARY KEY (sample_id, population_id)
);
"""


def init_db(data):
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        populate_db(conn, data)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def populate_db(conn, data):
    # Projects
    project_codes = sorted(data["project"].unique())
    conn.executemany(
        "INSERT INTO projects (project_code) VALUES (?)",
        [(code,) for code in project_codes],
    )

    project_ids = dict(conn.execute("SELECT project_code, id FROM projects").fetchall())

    # Subjects
    subjects = data[
        ["project", "subject", "condition", "age", "sex", "treatment", "response"]
    ].drop_duplicates()
    subject_rows = [
        (
            project_ids[row.project],
            row.subject,
            row.condition,
            int(row.age),
            row.sex,
            row.treatment,
            None if pd.isna(row.response) else row.response,
        )
        for row in subjects.itertuples(index=False)
    ]

    conn.executemany(
        """INSERT INTO subjects
           (project_id, subject_code, condition, age, sex, treatment, response)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        subject_rows,
    )

    subject_ids = dict(conn.execute("SELECT subject_code, id FROM subjects").fetchall())

    # Samples
    sample_rows = [
        (
            row.sample,
            row.sample_type,
            subject_ids[row.subject],
            int(row.time_from_treatment_start),
        )
        for row in data.itertuples(index=False)
    ]

    conn.executemany(
        """INSERT INTO samples
           (sample_code, sample_type, subject_id, time_from_treatment_start)
           VALUES (?, ?, ?, ?)""",
        sample_rows,
    )

    sample_ids = dict(conn.execute("SELECT sample_code, id FROM samples").fetchall())

    # Cell populations
    conn.executemany(
        "INSERT INTO cell_populations (population_name) VALUES (?)",
        [(population,) for population in POPULATIONS],
    )

    population_ids = dict(
        conn.execute("SELECT population_name, id FROM cell_populations").fetchall()
    )
    
    # Cell counts
    count_rows = [
        (
            sample_ids[row.sample],
            population_ids[population],
            int(getattr(row, population)),
        )
        for row in data.itertuples(index=False)
        for population in POPULATIONS
    ]

    conn.executemany(
        """INSERT INTO cell_counts (sample_id, population_id, cell_count)
           VALUES (?, ?, ?)""",
        count_rows,
    )


def main():
    data = pd.read_csv(CSV_PATH)
    print(f"Loaded CSV: {data.shape[0]} rows, {data.shape[1]} columns")
    init_db(data)
    print(f"Created database: {DB_PATH}")


if __name__ == "__main__":
    main()
