"""add jobs to signalsource enum

Revision ID: 0006_jobs_signal_source
Revises: 0005_company_profile_signal_source
Create Date: 2026-08-12

Adds 'jobs' as a value on the native Postgres enum backing `signals.source`,
for the new Jobs Collector (Greenhouse / Lever public job-board postings -
hiring signals for AI/ML, engineering, data, cloud/DevOps, security, and
general roles).

Same caveat as 0004/0005: Postgres requires ALTER TYPE ... ADD VALUE here
rather than a normal column migration, and this cannot be cleanly reversed -
downgrade() is intentionally a no-op.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006_jobs_signal_source"
down_revision: str | None = "0005_company_profile_signal_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE signalsource ADD VALUE IF NOT EXISTS 'jobs'")


def downgrade() -> None:
    # Deliberately not reversible - see module docstring / 0004's precedent.
    pass
