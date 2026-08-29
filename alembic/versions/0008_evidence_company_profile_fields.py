"""structured company-profile evidence fields

Revision ID: 0008_evidence_company_profile_fields
Revises: 0007_evidence_technology_jobs_fields
Create Date: 2026-08-29

Adds structured employee_count/founding_year columns to `evidence`,
populated by EvidenceNormalizer from the Company Profile Collector's
RawSignal.payload (homepage schema.org JSON-LD and/or Wikidata - see
app/services/evidence_normalizer.py and app/collectors/company_profile_collector.py).

These exist so ContradictionDetector can compare "two sources' employee
count" (or founding year) as the same structured field, rather than only
being able to compare loosely-matched narrative phrases. Nullable: most
evidence rows are not company-profile evidence, and existing rows have no
raw signal to backfill from.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_evidence_company_profile_fields"
down_revision: str | None = "0007_evidence_technology_jobs_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("employee_count", sa.Integer(), nullable=True))
    op.add_column("evidence", sa.Column("founding_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "founding_year")
    op.drop_column("evidence", "employee_count")
