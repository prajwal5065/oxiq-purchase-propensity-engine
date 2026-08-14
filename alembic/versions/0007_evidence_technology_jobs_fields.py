"""structured technology/jobs evidence fields

Revision ID: 0007_evidence_technology_jobs_fields
Revises: 0006_jobs_signal_source
Create Date: 2026-08-13

Adds structured Technology (technology_name, technology_provider) and Jobs
(job_title, job_department, job_location, job_ats_provider, job_posting_date)
columns to `evidence`. These sit alongside the existing signal_label/excerpt
text fields (kept as-is for backward compatibility) and are populated by
EvidenceNormalizer from the Tech/Jobs Collectors' RawSignal.payload - see
app/services/evidence_normalizer.py. All nullable: most evidence rows are
neither technology nor jobs evidence, and existing rows have no raw signal
to backfill from.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_evidence_technology_jobs_fields"
down_revision: str | None = "0006_jobs_signal_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("technology_name", sa.String(255), nullable=True))
    op.add_column("evidence", sa.Column("technology_provider", sa.String(50), nullable=True))

    op.add_column("evidence", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("evidence", sa.Column("job_department", sa.String(255), nullable=True))
    op.add_column("evidence", sa.Column("job_location", sa.String(255), nullable=True))
    op.add_column("evidence", sa.Column("job_ats_provider", sa.String(50), nullable=True))
    op.add_column("evidence", sa.Column("job_posting_date", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_evidence_technology_name", "evidence", ["technology_name"])


def downgrade() -> None:
    op.drop_index("ix_evidence_technology_name", table_name="evidence")

    op.drop_column("evidence", "job_posting_date")
    op.drop_column("evidence", "job_ats_provider")
    op.drop_column("evidence", "job_location")
    op.drop_column("evidence", "job_department")
    op.drop_column("evidence", "job_title")

    op.drop_column("evidence", "technology_provider")
    op.drop_column("evidence", "technology_name")
