from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth, candidate, companies, health
from app.config import get_frontend_path

app = FastAPI(
    title="Reverse HH API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(candidate.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")

frontend_path = get_frontend_path()
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
