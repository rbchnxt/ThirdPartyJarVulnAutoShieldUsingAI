from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import json
import joblib
import datetime
from pathlib import Path
from typing import List
import uuid

app = FastAPI()

# === Configurable Flags ===
ENABLE_OSV = True  # Set to False to skip OSV.dev querying

# === Load ML model ===
MODEL_PATH = "models/risk_model.pkl"
model = joblib.load(MODEL_PATH)

# === Dummy LLM-based advice (replace with real model if needed) ===
def generate_advice(lib, version, risk_score):
    if risk_score > 0.7:
        return f"Upgrade {lib} to a known stable release or latest version"
    elif risk_score > 0.4:
        return f"Review known issues in {lib}-{version} before use"
    else:
        return f"{lib}-{version} seems safe for use as of now"

# === Input schema ===
class ScanRequest(BaseModel):
    library: str
    version: str

# === Paths ===
RESULTS_DIR = Path("out/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# === OSV Querying ===
def query_osv(lib, version):
    import requests
    payload = {
        "version": version,
        "package": {"name": lib, "ecosystem": "Maven"}
    }
    try:
        resp = requests.post("https://api.osv.dev/v1/query", json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception:
        return {}

# === Scan Route ===
@app.post("/scan")
def scan(scan: ScanRequest):
    lib = scan.library
    ver = scan.version
    # Predict risk
    feature = [[len(lib), float(len(ver))]]
    risk_score = float(model.predict_proba(feature)[0][1])

    # Advice
    advice = generate_advice(lib, ver, risk_score)

    # OSV
    osv_data = query_osv(lib, ver) if ENABLE_OSV else {}

    return {
        "library": lib,
        "version": ver,
        "risk_score": round(risk_score, 2),
        "recommendation": advice,
        "osv": osv_data
    }

# === HTML Results View ===
@app.get("/", response_class=HTMLResponse)
def results_home():
    files = sorted(RESULTS_DIR.glob("*.html"), reverse=True)
    links = [
        f'<li><a href="/results/{f.name}" target="_blank">{f.name}</a></li>'
        for f in files
    ]
    return f"""
    <html><body>
        <h1>Scan Results</h1>
        <ul>{''.join(links)}</ul>
    </body></html>
    """

@app.get("/results/{filename}", response_class=HTMLResponse)
def get_result_file(filename: str):
    filepath = RESULTS_DIR / filename
    if not filepath.exists():
        return HTMLResponse(content="Result file not found", status_code=404)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    content += '<br><a href="/">← Back to Results Home</a>'
    return HTMLResponse(content=content)

