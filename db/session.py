from pathlib import Path

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def get_engine(database_url: str):
    return create_engine(sqlalchemy_url(database_url), pool_pre_ping=True)


def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), autoflush=False, autocommit=False)


def run_migrations(database_url: str) -> None:
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for migration in migrations:
                statements = [s.strip() for s in migration.read_text().split(";") if s.strip()]
                for statement in statements:
                    cur.execute(statement)
        conn.commit()
