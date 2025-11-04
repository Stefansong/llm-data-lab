from databases import Database
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings

settings = get_settings()

metadata = MetaData()
engine = create_engine(
    settings.database_url.replace("aiosqlite", "pysqlite"), future=True, echo=False
)
database = Database(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
