from sqlmodel import SQLModel, Session, create_engine
from app.core.config import DATABASE_URL
import os

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
else:
    # PostgreSQL configuration (for production)
    engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    # --- FIX ---
    # We import the models module here to ensure that all table models are
    # registered with SQLModel's metadata before we try to create the tables.
    from app.db import models
    # -----------
    
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session