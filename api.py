from fastapi import FastAPI
import json
from analysis import (get_baseline_subset, get_form_answer, get_responder_comparison)

app = FastAPI(title="Immune Cell Response Dashboard")

def dataframe_records(dataframe):
    return json.loads(
        dataframe.to_json(orient="records", double_precision=6,)
    )

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

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