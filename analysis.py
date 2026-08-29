import sqlite3
from pathlib import Path
import pandas as pd
from scipy.stats import mannwhitneyu


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
    
    
def get_responder_comparison():
    freq = get_population_frequencies()
    
    metadata_query = """
    SELECT
        samples.sample_code AS sample,
        projects.project_code AS project,
        subjects.subject_code AS subject,
        subjects.condition,
        subjects.treatment,
        subjects.response,
        samples.sample_type
    FROM samples
    JOIN subjects ON subjects.id = samples.subject_id
    JOIN projects ON projects.id = subjects.project_id
    """
    
    with sqlite3.connect(DB_PATH) as conn:
        metadata = pd.read_sql_query(metadata_query, conn)
        
    data = freq.merge(metadata, on="sample", validate="many_to_one")
    
    filtered = data[
        (data["condition"] == "melanoma")
        & (data["treatment"] == "miraclib")
        & (data["sample_type"] == "PBMC")
        & (data["response"].isin(["yes", "no"]))
    ]
    
    subject_freq = (
        filtered.groupby(
            ["project", "subject", "response", "population"], as_index=False,
        )["percentage"].mean().rename(columns={"percentage": "mean_percentage"})
    )
    
    results = []
    
    for population, group in subject_freq.groupby("population"):
        responders = group.loc[group["response"] == "yes", "mean_percentage"]
        nonresponders = group.loc[group["response"] == "no", "mean_percentage"]
        test = mannwhitneyu(
            responders,
            nonresponders,
            alternative="two-sided",
        )

        results.append(
            {
                "population": population,
                "responders_n": len(responders),
                "nonresponders_n": len(nonresponders),
                "responders_median": responders.median(),
                "nonresponders_median": nonresponders.median(),
                "median_difference": (
                    responders.median() - nonresponders.median()
                ),
                "mann_whitney_u": test.statistic,
                "p_value": test.pvalue,
            }
        )
        
    statistics = pd.DataFrame(results)
    
    # Bonferroni correction for the five population comparisons.
    statistics["adjusted_p_value"] = (
        statistics["p_value"] * len(statistics)
    ).clip(upper=1)

    statistics["significant"] = (
        statistics["adjusted_p_value"] < 0.05
    )
    
    return subject_freq, statistics


def main():
    summary = get_population_frequencies()
    print(summary.head())
    print(f"Rows: {len(summary)}")
    
    subject_frequencies, statistics = get_responder_comparison()

    print(subject_frequencies.head())
    print(statistics.to_string(index=False))
    
if __name__ == "__main__":
    main()
    