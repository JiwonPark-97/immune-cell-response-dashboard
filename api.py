from fastapi import FastAPI
import json
from analysis import get_responder_comparison

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