# app/db.py
import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medbot.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    course_name = Column(String(100))
    content_type = Column(String(50))  # pdf, reference, video...
    file_id = Column(String(200))

def init_db():
    Base.metadata.create_all(bind=engine)
