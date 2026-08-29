import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "immune-cells.db"

def get_population_frequencies():
    query = """
    WITH sample_totals AS (
        SELECT sample_id, SUM(cell_count) AS total_count
        FROM cell_counts
        GROUP BY sample_id
    )
    SELECT
        s.sample_code AS sample,
        totals.total_count,
        populations.population_name AS population,
        counts.cell_count AS count,
        100.0 * counts.cell_count / NULLIF(totals.total_count, 0) AS percentage
    FROM cell_counts AS counts
    JOIN samples AS s ON s.id = counts.sample_id
    JOIN cell_populations AS populations ON populations.id = counts.population_id
    JOIN sample_totals AS totals ON totals.sample_id = counts.sample_id
    ORDER BY s.sample_code, populations.id
    """
    
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)
    
    
def main():
    summary = get_population_frequencies()
    print(summary.head())
    print(f"Rows: {len(summary)}")
    
    # rows_per_sample = summary.groupby("sample").size()
    # print(rows_per_sample.value_counts())
    # assert rows_per_sample.eq(5).all()

    # summary.to_csv("population_freq.csv", index=False)
if __name__ == "__main__":
    main()
    