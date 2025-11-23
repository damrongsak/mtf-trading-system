from fastapi import FastAPI

app = FastAPI(title="Data Pipeline Service")

@app.get("/health")
def health_check():
    return {"status": "ok"}
