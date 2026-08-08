"""add github to signalsource enum

Revision ID: 0004_github_signal_source
Revises: 0003_analysis_explanation
Create Date: 2026-08-08

Adds 'github' as a value on the native Postgres enum backing
`signals.source`, for the new GitHub Collector (Stage 13/14 of the
evidence-first spec - "no key needed" development-signal source).

Postgres requires ALTER TYPE ... ADD VALUE for this rather than a normal
column migration, and - unlike every other migration in this repo -
genuinely cannot be cleanly reversed: Postgres does not support removing a
single value from an enum type without rebuilding the type (and any rows
using it) from scratch, so `downgrade()` is intentionally a no-op with an
explanatory comment rather than pretending to revert safely. If a real
rollback is ever needed, it means recreating the enum type and remapping
any 'github' rows first - not just running this file backwards.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004_github_signal_source"
down_revision: str | None = "0003_analysis_explanation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE signalsource ADD VALUE IF NOT EXISTS 'github'")


def downgrade() -> None:
    # Deliberately not reversible - see module docstring. Removing an enum
    # value in Postgres requires rebuilding the type and any dependent rows,
    # which is a data decision, not something a migration should do silently.
    pass
