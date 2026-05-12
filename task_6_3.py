"""
Задание 6.3 — Управление документацией через MODE (DEV/PROD)
"""

import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

MODE = os.getenv("MODE", "DEV").upper()
if MODE not in ("DEV", "PROD"):
    raise RuntimeError(f"Invalid MODE={MODE!r}. Must be DEV or PROD.")

DOCS_USER = os.getenv("DOCS_USER", "docs_admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "docs_secret")

# Отключаем встроенную документацию — управляем сами
app = FastAPI(
    title="Task 6.3 — Docs Access Control",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

security = HTTPBasic()


def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, DOCS_USER)
    ok_pass = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


if MODE == "DEV":

    @app.get("/docs", include_in_schema=False)
    def custom_docs(_: None = Depends(verify_docs_credentials)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

    @app.get("/openapi.json", include_in_schema=False)
    def custom_openapi(_: None = Depends(verify_docs_credentials)):
        schema = get_openapi(title=app.title, version="0.1.0", routes=app.routes)
        return JSONResponse(schema)

else:  # PROD
    @app.get("/docs", include_in_schema=False)
    @app.get("/openapi.json", include_in_schema=False)
    @app.get("/redoc", include_in_schema=False)
    def docs_disabled():
        raise HTTPException(status_code=404, detail="Not Found")


# ── Sample business endpoint ─────────────────────────────────────────────────

@app.get("/ping")
def ping():
    return {"status": "ok", "mode": MODE}