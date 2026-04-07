# app/database/master_db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.master_models import MasterBase

engine = create_engine(settings.MASTER_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_master_db():
    MasterBase.metadata.create_all(bind=engine)