import pytest
from pydantic import ValidationError

from backend.app.schemas import CandidateInput


def test_candidate_schema_accepts_only_interview_features():
    candidate = CandidateInput(
        technicalScore=82,
        priorBpoExperienceYears=1.5,
        campaign="Atención digital",
        preferredShift="day",
        scheduleAvailability="flexible",
    )
    assert candidate.technicalScore == 82


def test_candidate_schema_rejects_post_interview_supervisor_and_protected_fields():
    with pytest.raises(ValidationError):
        CandidateInput(
            technicalScore=82,
            priorBpoExperienceYears=1.5,
            campaign="Atención digital",
            preferredShift="day",
            scheduleAvailability="flexible",
            supervisor="Sup. A",
            age=25,
        )
