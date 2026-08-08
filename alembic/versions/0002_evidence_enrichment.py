"""evidence enrichment columns

Revision ID: 0002_evidence_enrichment
Revises: 0001_initial
Create Date: 2026-08-08

Adds category/collector/pillar/published_at to `evidence`, per the
evidence-first architecture upgrade: these are what let the SignalAggregator
group evidence and the (future) dashboard show per-pillar, per-source
breakdowns instead of a flat quote list. Hand-written for the same reason as
0001_initial - no live Postgres in this environment to autogenerate against.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_evidence_enrichment"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("evidence", sa.Column("collector", sa.String(50), nullable=True))
    op.add_column("evidence", sa.Column("pillar", sa.String(50), nullable=True))
    op.add_column("evidence", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_evidence_category", "evidence", ["category"])
    op.create_index("ix_evidence_collector", "evidence", ["collector"])
    op.create_index("ix_evidence_pillar", "evidence", ["pillar"])


def downgrade() -> None:
    op.drop_index("ix_evidence_pillar", table_name="evidence")
    op.drop_index("ix_evidence_collector", table_name="evidence")
    op.drop_index("ix_evidence_category", table_name="evidence")

    op.drop_column("evidence", "published_at")
    op.drop_column("evidence", "pillar")
    op.drop_column("evidence", "collector")
    op.drop_column("evidence", "category")
