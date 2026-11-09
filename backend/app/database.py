from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "data.db"

engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
SessionLocal = sessionmaker(bind=engine)
