from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import init_db
from app.routers import datasets

app = FastAPI(
    title="KarhutlaWatch API",
    description="Backend API untuk pemantauan dan prediksi risiko karhutla Indonesia (Hadoop HDFS, Spark, NiFi)",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/docs/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "KarhutlaWatch API",
        "hdfs_uri": settings.HDFS_URI,
        "spark_master": settings.SPARK_MASTER
    }

app.include_router(datasets.router, prefix="/api")

