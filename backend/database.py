import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in .env file")

# create engine
engine = create_engine(DATABASE_URL, echo=True)


# Alembic helper
def run_migrations():
    """Run Alembic migrations programmatically on startup."""
    alembic_cfg = Config("alembic.ini")  # points to alembic.ini
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")  # apply all migrations


# Dependency for FastAPI routes
def get_session():
    with Session(engine) as session:
        yield session


# Startup initializer
def init_db():
    # Instead of create_all(), we now use Alembic migrations
    run_migrations()
