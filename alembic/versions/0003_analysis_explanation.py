"""analysis explanations table

Revision ID: 0003_analysis_explanation
Revises: 0002_evidence_enrichment
Create Date: 2026-08-08

Adds the analysis_explanations table backing the evidence-first
"explain everything" layer (Phase 2): one JSON-payload row per analysis
run, storing the full AnalysisExplanation bundle (coverage, confidence,
pillar attribution, disqualification reasoning) so the dossier page can
read it back without re-running the analysis. Hand-written, same caveat as
0001_initial and 0002_evidence_enrichment.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_analysis_explanation"
down_revision: str | None = "0002_evidence_enrichment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_explanations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_analysis_explanations_company_id", "analysis_explanations", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_explanations_company_id", table_name="analysis_explanations")
    op.drop_table("analysis_explanations")
