"""Check the signalsource enum values in PostgreSQL and the alembic version."""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
import os

db_url = os.environ["DATABASE_URL_SYNC"]
engine = create_engine(db_url)

with engine.connect() as conn:
    q1 = text(
        "SELECT enumlabel FROM pg_enum "
        "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
        "WHERE pg_type.typname = 'signalsource' "
        "ORDER BY enumsortorder"
    )
    result = conn.execute(q1)
    values = [r[0] for r in result]
    print("signalsource enum values in DB:", values)

    q2 = text("SELECT version_num FROM alembic_version ORDER BY version_num")
    result2 = conn.execute(q2)
    versions = [r[0] for r in result2]
    print("alembic_version rows:", versions)
