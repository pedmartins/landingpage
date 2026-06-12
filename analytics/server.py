"""
server.py — Servidor FastAPI para templates HTML
=================================================
Serve ficheiros HTML estáticos da directoria local.
"""

import uvicorn
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def log(msg: str) -> None:
    logging.info(msg)

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LinkWith HTML Server",
    description="Servidor de templates HTML.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent

# ─── Páginas HTML ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Apps"])
async def index():
    html = STATIC_DIR / "leads_gestao.html"
    if html.exists():
        log("📄 A servir leads_gestao.html")
        return FileResponse(html)
    raise HTTPException(status_code=404, detail="leads_gestao.html não encontrado.")

@app.get("/modelos-ui", tags=["Apps"])
async def modelos_ui():
    html = STATIC_DIR / "modelos_comunicacao.html"
    if html.exists():
        log("📄 A servir modelos_comunicacao.html")
        return FileResponse(html)
    raise HTTPException(status_code=404, detail="modelos_comunicacao.html não encontrado.")

@app.get("/analytics", tags=["Apps"])
async def analytics():
    html = STATIC_DIR / "cf-dashboard.html"
    if html.exists():
        log("📄 A servir cf-dashboard.html")
        return FileResponse(html)
    raise HTTPException(status_code=404, detail="cf-dashboard.html não encontrado.")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    f = STATIC_DIR / "favicon.ico"
    if f.exists():
        return FileResponse(f)
    raise HTTPException(status_code=204)

# ─── Arranque ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log("🚀 A iniciar LinkWith HTML Server na porta 8003...")
    uvicorn.run("server:app", host="0.0.0.0", port=8003, reload=False, log_level="info")
