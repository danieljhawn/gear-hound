from fastapi import FastAPI

app = FastAPI(title="Gear Hound")


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gear-hound"}
