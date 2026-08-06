import pytest
from pydantic import ValidationError

from app.schemas.evidence import EvidenceItem


def test_evidence_item_requires_confidence_in_range():
    with pytest.raises(ValidationError):
        EvidenceItem(signal_label="x", excerpt="y", source="z", confidence=1.5)


def test_evidence_item_rejects_blank_excerpt():
    with pytest.raises(ValidationError):
        EvidenceItem(signal_label="x", excerpt="   ", source="z", confidence=0.5)


def test_evidence_item_accepts_valid_payload():
    item = EvidenceItem(signal_label="Hiring AI Engineers", excerpt="we are hiring", source="Careers", confidence=0.8)
    assert item.confidence == 0.8
