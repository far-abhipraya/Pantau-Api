from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

settings.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{settings.SQLITE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_type = Column(String(50), nullable=False)  # firms_hist, firms_nrt, weather, generic
    hdfs_path = Column(String(512), nullable=False)
    size_bytes = Column(BigInteger, default=0)
    row_count = Column(BigInteger, default=0)
    column_count = Column(Integer, default=0)
    columns_json = Column(Text, default="[]")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), default="queued")  # queued, running, success, failed
    config_json = Column(Text, default="{}")
    report_json = Column(Text, default="{}")
    log_tail = Column(Text, default="")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

