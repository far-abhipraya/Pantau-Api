"""Aplikasi FastAPI PantauApi."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import (
    analytics,
    datasets,
    geo,
    health,
    ingest,
    jobs,
    map as map_routes,
    preprocessing,
    quarantine,
    sources,
)
from app.core.config import settings
from app.pipeline.scheduler import scheduler
from app.services import serving


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_dirs()
    try:
        serving.ensure_views(force=True)
    except Exception as exc:  # serving layer belum dibuat: API tetap hidup
        print(f"[WARN] Serving layer belum siap: {exc}")
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(
    title="PantauApi",
    description="API pemantauan hotspot karhutla Indonesia",
    version="1.2.1",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(map_routes.router, prefix=settings.API_PREFIX)
app.include_router(geo.router, prefix=settings.API_PREFIX)
app.include_router(sources.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(datasets.router, prefix=settings.API_PREFIX)
app.include_router(preprocessing.router, prefix=settings.API_PREFIX)
app.include_router(jobs.router, prefix=settings.API_PREFIX)
app.include_router(quarantine.router, prefix=settings.API_PREFIX)
app.include_router(ingest.router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": settings.PROJECT_NAME, "docs": "/docs", "api": settings.API_PREFIX}
