from fastapi import FastAPI

app = FastAPI(title="Immune Cell Response Dashboard")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}