import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models.orm import Base

DB_DIR = "data"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DATABASE_URL = f"sqlite+aiosqlite:///./{DB_DIR}/traceai_demo.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30},
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

MIGRATIONS = [
    "ALTER TABLE ai_reports ADD COLUMN incident_id VARCHAR(50)",
    "ALTER TABLE ai_reports ADD COLUMN evidence_json TEXT",
    "ALTER TABLE ai_reports ADD COLUMN gemma_model VARCHAR(50)",
    "ALTER TABLE ai_reports ADD COLUMN tools_used_json TEXT",
    "ALTER TABLE system_state ADD COLUMN incident_id VARCHAR(50)",
]


async def _run_migrations(conn):
    for stmt in MIGRATIONS:
        try:
            await conn.execute(text(stmt))
        except Exception:
            pass


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)


async def get_db():
    async with async_session() as session:
        yield session
