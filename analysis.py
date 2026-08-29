"""Run the required immune-cell analyses and write reproducible outputs."""

import json
import sqlite3
from contextlib import closing
from html import escape
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "immune-cells.db"
OUTPUT_DIR = ROOT / "output"
FIGURE_DIR = OUTPUT_DIR / "figures"
POPULATIONS = ["b_cell", "cd4_t_cell", "cd8_t_cell", "monocyte", "nk_cell"]


def get_population_frequencies():
    """Return one row per sample and cell population with relative frequency."""
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
    
    with closing(sqlite3.connect(DB_PATH)) as connection:
        return pd.read_sql_query(query, connection)
    
    
def get_responder_comparison(frequencies=None):
    """Compare subject-level frequencies between response groups."""
    if frequencies is None:
        frequencies = get_population_frequencies()
    
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
    
    with closing(sqlite3.connect(DB_PATH)) as connection:
        metadata = pd.read_sql_query(metadata_query, connection)
        
    data = frequencies.merge(metadata, on="sample", validate="many_to_one")
    
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
    
    for population in POPULATIONS:
        group = subject_freq[subject_freq["population"] == population]
        responders = group.loc[group["response"] == "yes", "mean_percentage"]
        nonresponders = group.loc[group["response"] == "no", "mean_percentage"]
        if responders.empty or nonresponders.empty:
            raise ValueError(f"Both response groups are required for {population}")
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
                "mann_whitney_u": float(test.statistic),
                "p_value": float(test.pvalue),
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


def get_baseline_subset():
    """Return the baseline subset and its project/demographic counts."""
    query = """
    SELECT
        projects.project_code AS project,
        subjects.subject_code AS subject,
        samples.sample_code AS sample,
        subjects.response,
        subjects.sex
    FROM samples
    JOIN subjects ON subjects.id = samples.subject_id
    JOIN projects ON projects.id = subjects.project_id
    WHERE subjects.condition = 'melanoma'
      AND subjects.treatment = 'miraclib'
      AND samples.sample_type = 'PBMC'
      AND samples.time_from_treatment_start = 0
    ORDER BY projects.project_code, subjects.subject_code
    """

    with closing(sqlite3.connect(DB_PATH)) as connection:
        subset = pd.read_sql_query(query, connection)

    project_counts = (
        subset.groupby("project")["sample"]
        .nunique()
        .reset_index(name="count")
        .rename(columns={"project": "group"})
        .assign(breakdown="project")
    )

    response_counts = (
        subset.groupby("response")["subject"]
        .nunique()
        .reset_index(name="count")
        .rename(columns={"response": "group"})
        .assign(breakdown="response")
    )

    sex_counts = (
        subset.groupby("sex")["subject"]
        .nunique()
        .reset_index(name="count")
        .rename(columns={"sex": "group"})
        .assign(breakdown="sex")
    )

    counts = pd.concat(
        [project_counts, response_counts, sex_counts],
        ignore_index=True,
    )[["breakdown", "group", "count"]]

    return subset, counts


def get_form_answer():
    """Calculate the separate B-cell average requested by the form."""
    query = """
    SELECT
        AVG(cell_counts.cell_count) AS average_b_cells,
        COUNT(*) AS sample_count
    FROM cell_counts
    JOIN cell_populations
        ON cell_populations.id = cell_counts.population_id
    JOIN samples
        ON samples.id = cell_counts.sample_id
    JOIN subjects
        ON subjects.id = samples.subject_id
    WHERE subjects.condition = 'melanoma'
      AND subjects.sex = 'M'
      AND subjects.response = 'yes'
      AND samples.time_from_treatment_start = 0
      AND cell_populations.population_name = 'b_cell'
    """

    with closing(sqlite3.connect(DB_PATH)) as connection:
        average, sample_count = connection.execute(query).fetchone()

    if average is None:
        raise ValueError("No samples match the form calculation filters")
    return float(average), int(sample_count)


def _box_statistics(values):
    """Return quartiles, whiskers, and outliers for one SVG box."""
    q1 = float(values.quantile(0.25))
    median = float(values.median())
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    inliers = values[
        (values >= q1 - 1.5 * iqr) & (values <= q3 + 1.5 * iqr)
    ]
    outliers = values[~values.index.isin(inliers.index)]
    return q1, median, q3, float(inliers.min()), float(inliers.max()), outliers


def save_boxplot(subject_frequencies):
    """Write the required responder comparison as a standalone SVG boxplot."""
    width, height = 1200, 650
    left, right, top, bottom = 90, 30, 85, 100
    plot_width = width - left - right
    plot_height = height - top - bottom
    y_max = max(45.0, float(subject_frequencies["mean_percentage"].max()) + 2)

    def x_position(index, response):
        center = left + plot_width * (index + 0.5) / len(POPULATIONS)
        return center + (-22 if response == "yes" else 22)

    def y_position(value):
        return top + plot_height * (1 - value / y_max)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}'
        '.tick{font-size:13px;fill:#52637c}.label{font-size:15px}'
        '.title{font-size:22px;font-weight:600}</style>',
        f'<text x="{width / 2}" y="36" text-anchor="middle" class="title">'
        'Melanoma PBMC: responders vs non-responders</text>',
    ]

    for tick in range(0, int(y_max) + 1, 5):
        y = y_position(tick)
        elements.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" '
                f'y2="{y:.1f}" stroke="#e5eaf1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" '
                f'class="tick">{tick}</text>',
            ]
        )

    colors = {"yes": "#2563eb", "no": "#e8793e"}
    for index, population in enumerate(POPULATIONS):
        for response in ("yes", "no"):
            values = subject_frequencies.loc[
                (subject_frequencies["population"] == population)
                & (subject_frequencies["response"] == response),
                "mean_percentage",
            ]
            q1, median, q3, low, high, outliers = _box_statistics(values)
            x = x_position(index, response)
            color = colors[response]
            box_top = y_position(q3)
            box_bottom = y_position(q1)
            elements.extend(
                [
                    f'<line x1="{x}" y1="{y_position(high):.1f}" x2="{x}" '
                    f'y2="{y_position(low):.1f}" stroke="{color}" stroke-width="2"/>',
                    f'<rect x="{x - 15}" y="{box_top:.1f}" width="30" '
                    f'height="{box_bottom - box_top:.1f}" fill="{color}" '
                    f'fill-opacity="0.24" stroke="{color}" stroke-width="2"/>',
                    f'<line x1="{x - 15}" y1="{y_position(median):.1f}" '
                    f'x2="{x + 15}" y2="{y_position(median):.1f}" '
                    f'stroke="{color}" stroke-width="3"/>',
                    f'<line x1="{x - 10}" y1="{y_position(low):.1f}" '
                    f'x2="{x + 10}" y2="{y_position(low):.1f}" stroke="{color}"/>',
                    f'<line x1="{x - 10}" y1="{y_position(high):.1f}" '
                    f'x2="{x + 10}" y2="{y_position(high):.1f}" stroke="{color}"/>',
                ]
            )
            for value in outliers:
                elements.append(
                    f'<circle cx="{x}" cy="{y_position(float(value)):.1f}" '
                    f'r="3" fill="{color}" fill-opacity="0.8"/>'
                )

        center = left + plot_width * (index + 0.5) / len(POPULATIONS)
        elements.append(
            f'<text x="{center:.1f}" y="{height - 62}" text-anchor="middle" '
            f'class="tick">{escape(population)}</text>'
        )

    elements.extend(
        [
            f'<text x="{width / 2}" y="{height - 22}" text-anchor="middle" '
            'class="label">Cell population</text>',
            f'<text x="24" y="{top + plot_height / 2}" text-anchor="middle" '
            f'transform="rotate(-90 24 {top + plot_height / 2})" class="label">'
            'Mean relative frequency (%)</text>',
            f'<rect x="{width - 260}" y="48" width="14" height="14" '
            'fill="#2563eb"/>',
            f'<text x="{width - 238}" y="60" class="tick">Responder</text>',
            f'<rect x="{width - 150}" y="48" width="14" height="14" '
            'fill="#e8793e"/>',
            f'<text x="{width - 128}" y="60" class="tick">Non-responder</text>',
            '</svg>',
        ]
    )
    (FIGURE_DIR / "responder_vs_nonresponder_boxplot.svg").write_text(
        "\n".join(elements),
        encoding="utf-8",
    )


def write_outputs(summary, subject_frequencies, statistics, subset, counts, form):
    """Write all required tables, plot, and a concise analysis report."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_DIR / "cell_population_frequencies.csv", index=False)
    subject_frequencies.to_csv(
        OUTPUT_DIR / "part3_subject_mean_frequencies.csv",
        index=False,
    )
    statistics.to_csv(OUTPUT_DIR / "part3_statistics.csv", index=False)
    subset.to_csv(OUTPUT_DIR / "part4_baseline_samples.csv", index=False)
    counts.to_csv(OUTPUT_DIR / "part4_counts.csv", index=False)
    (OUTPUT_DIR / "form_answer.json").write_text(
        json.dumps(form, indent=2) + "\n",
        encoding="utf-8",
    )
    save_boxplot(subject_frequencies)

    significant = statistics.loc[statistics["significant"], "population"].tolist()
    conclusion = ", ".join(significant) if significant else "None"
    report = f"""# Analysis results

## Part 2

The population-frequency table contains {len(summary):,} rows.

## Part 3

Significant populations after Bonferroni correction: **{conclusion}**.

## Part 4

The baseline subset contains {len(subset):,} samples.

## Form calculation

Average B-cell count: **{form['average_b_cells']:.2f}**

Samples included: **{form['sample_count']}**
"""
    (OUTPUT_DIR / "analysis_results.md").write_text(report, encoding="utf-8")


def main():
    summary = get_population_frequencies()
    subject_frequencies, statistics = get_responder_comparison(summary)
    subset, counts = get_baseline_subset()
    average_b_cells, sample_count = get_form_answer()
    form = {
        "average_b_cells": round(average_b_cells, 2),
        "sample_count": sample_count,
    }
    write_outputs(
        summary,
        subject_frequencies,
        statistics,
        subset,
        counts,
        form,
    )
    print(f"Wrote analysis outputs to {OUTPUT_DIR}")
    print(f"Form answer: {average_b_cells:.2f} ({sample_count} samples)")


if __name__ == "__main__":
    main()
