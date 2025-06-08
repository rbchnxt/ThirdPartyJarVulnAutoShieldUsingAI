from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from pathlib import Path
import json

app = FastAPI()
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    files = sorted(results_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)
    links = [f'<li><a href="/results/{f.name}">{f.name}</a></li>' for f in files]
    return f"<h1>Results Home</h1><ul>{''.join(links)}</ul>"

@app.get("/results/{file_name}", response_class=HTMLResponse)
async def get_result(file_name: str):
    file_path = results_dir / file_name
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content + '<br><a href="/">Back to Home</a>'
    return "File not found."
