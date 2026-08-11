"""add company_profile to signalsource enum

Revision ID: 0005_company_profile_signal_source
Revises: 0004_github_signal_source
Create Date: 2026-08-11

Adds 'company_profile' as a value on the native Postgres enum backing
`signals.source`, for the new Company & Technology Intelligence Collector
(company size/capacity, industry/profile, cloud/AI/ML tech, digital
maturity signals sourced from schema.org markup and public company
registries).

Same caveat as 0004_github_signal_source: Postgres requires ALTER TYPE ...
ADD VALUE here rather than a normal column migration, and this cannot be
cleanly reversed - downgrade() is intentionally a no-op.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005_company_profile_signal_source"
down_revision: str | None = "0004_github_signal_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE signalsource ADD VALUE IF NOT EXISTS 'company_profile'")


def downgrade() -> None:
    # Deliberately not reversible - see module docstring / 0004's precedent.
    pass
