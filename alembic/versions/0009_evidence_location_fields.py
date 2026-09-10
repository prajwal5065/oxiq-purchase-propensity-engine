"""structured evidence location fields (headquarters vs office)

Revision ID: 0009_evidence_location_fields
Revises: 0008_evidence_company_profile_fields
Create Date: 2026-08-30

Adds `location_kind` ('headquarters' | 'office') and `location_name` to
`evidence`, populated by EvidenceNormalizer:

- 'headquarters' comes only from the Company Profile Collector's
  structured schema.org address / Wikidata P159 signal - an authoritative
  claim about where the company is headquartered.
- 'office' comes only from the Jobs Collector's per-posting location - a
  hiring/office presence, which is evidence of a facility, never proof of
  headquarters.

Keeping these as two distinct values (rather than one generic "location"
field) is what lets the report - and ContradictionDetector, which now
also compares headquarters claims across sources - avoid conflating "we
have an office/facility here" with "we are headquartered here".
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_evidence_location_fields"
down_revision: str | None = "0008_evidence_company_profile_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("location_kind", sa.String(length=20), nullable=True))
    op.add_column("evidence", sa.Column("location_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "location_name")
    op.drop_column("evidence", "location_kind")
