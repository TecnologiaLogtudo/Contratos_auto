from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# No Windows, o Playwright precisa do ProactorEventLoop para subprocessos de navegador
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router as api_router
from .infrastructure.broadcaster import broadcaster
from .infrastructure.database import BASE_STORAGE_DIR, db


BASE_PATH = os.getenv('BASE_PATH', '').strip()
if BASE_PATH and not BASE_PATH.startswith('/'):
    BASE_PATH = f'/{BASE_PATH}'
BASE_PATH = BASE_PATH.rstrip('/') if BASE_PATH != '/' else ''

app = FastAPI(title="LogTudo Contratos_auto API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Inicializa banco SQLite e loop de eventos para o broadcaster."""
    db.init_db()
    try:
        broadcaster.set_event_loop(asyncio.get_running_loop())
    except Exception:
        pass


# Registra rotas REST e WebSockets da Nova Arquitetura
app.include_router(api_router, prefix="/api/v2")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)
if BASE_PATH:
    app.include_router(api_router, prefix=f"{BASE_PATH}/api/v2")
    app.include_router(api_router, prefix=f"{BASE_PATH}/api")
    app.include_router(api_router, prefix=BASE_PATH)


# Diretórios do Frontend e Assets Estáticos
web_dir = Path(__file__).resolve().parents[2] / "web"
dist_dir = web_dir / "dist"
public_dir = web_dir / "public"
index_dist_path = dist_dir / "index.html"
index_path = index_dist_path if index_dist_path.exists() else web_dir / "index.html"

# Monta assets do Vite se compilados
if (dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="web-dist-assets")
elif (web_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(web_dir / "assets")), name="web-src-assets")

# Monta arquivos públicos da marca (logos, texturas)
if (public_dir / "brand").exists():
    app.mount("/brand", StaticFiles(directory=str(public_dir / "brand")), name="brand-public-assets")
elif (dist_dir / "brand").exists():
    app.mount("/brand", StaticFiles(directory=str(dist_dir / "brand")), name="brand-dist-assets")


def _render_index_html() -> HTMLResponse:
    if not index_path.exists():
        return HTMLResponse("<h1>LogTudo Contratos_auto Backend Ativo</h1><p>Frontend não compilado ainda. Execute 'npm run build' na pasta web.</p>")
    content = index_path.read_text(encoding="utf-8")
    base_script = f'<script>window.LOGTUDO_BASE_PATH = "{BASE_PATH or ""}";</script>'
    if "window.LOGTUDO_BASE_PATH" not in content:
        if "</head>" in content:
            content = content.replace("</head>", f"  {base_script}\n  </head>")
        else:
            content = f"{base_script}\n{content}"
    return HTMLResponse(content)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "LogTudo Contratos_auto", "version": "2.0.0"}


@app.get("/health/ready")
def health_ready() -> dict:
    return {"status": "ready"}


@app.get("/")
def serve_index():
    return _render_index_html()


@app.get("/manual")
def serve_manual():
    return _render_index_html()


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "health", "assets/", "brand/", "ws/")):
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    return _render_index_html()
