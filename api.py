import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

from analysis import (
    get_baseline_subset,
    get_form_answer,
    get_population_frequencies,
    get_responder_comparison,
)


app = FastAPI(title="Immune Cell Response Dashboard")
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


def dataframe_records(dataframe):
    return json.loads(
        dataframe.to_json(orient="records", double_precision=6)
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/population-frequencies")
def population_frequencies(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    sample: str = "",
):
    frequencies = get_population_frequencies()
    if sample:
        frequencies = frequencies[
            frequencies["sample"].str.contains(sample, case=False, regex=False)
        ]

    total = len(frequencies)
    page = frequencies.iloc[offset : offset + limit]
    return {
        "records": dataframe_records(page),
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/responder-comparison")
def responder_comparison():
    frequencies, statistics = get_responder_comparison()

    return {
        "frequencies": dataframe_records(frequencies),
        "statistics": dataframe_records(statistics),
    }


@app.get("/api/baseline-analysis")
def baseline_analysis():
    samples, counts = get_baseline_subset()
    average_b_cells, sample_count = get_form_answer()

    return {
        "samples": dataframe_records(samples),
        "counts": dataframe_records(counts),
        "form_calculation": {
            "average_b_cells": round(average_b_cells, 2),
            "sample_count": sample_count,
        },
    }


if FRONTEND_DIST.exists():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )
