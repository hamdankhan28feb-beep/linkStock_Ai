from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import re

def _build_engine():
    raw = settings.DATABASE_URL
    # Try to parse postgresql://user:password@host:port/dbname
    # Using regex to safely extract parts and pass to URL.create()
    m = re.match(
        r"postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+):(?P<port>\d+)/(?P<db>.+)",
        raw
    )
    if m:
        url = URL.create(
            drivername="postgresql",
            username=m.group("user"),
            password=m.group("password"),   # SQLAlchemy handles escaping
            host=m.group("host"),
            port=int(m.group("port")),
            database=m.group("db"),
        )
    else:
        url = raw  # fallback

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
