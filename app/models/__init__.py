"""Import every ORM model here so SQLAlchemy's mapper registry can resolve
string-based relationship() references regardless of import order elsewhere
in the app (Alembic autogenerate, tests, etc. only need `import app.models`).
"""
from app.models.analysis_explanation import AnalysisExplanationRecord
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.company import Company
from app.models.evidence import Evidence
from app.models.recommendation import Recommendation
from app.models.score import Score, ScoreType
from app.models.signal import Signal, SignalSource

__all__ = [
    "AnalysisExplanationRecord",
    "AnalysisJob",
    "Company",
    "Evidence",
    "JobStatus",
    "Recommendation",
    "Score",
    "ScoreType",
    "Signal",
    "SignalSource",
]
