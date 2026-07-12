from app.domain.applications import APPLICATION_STATUSES
from app.models.enums import ApplicationStatus


def test_application_statuses_match_state_machine():
    expected = {
        "sent",
        "viewed",
        "accepted",
        "rejected",
        "auto_rejected",
        "expired",
        "reactivation_requested",
        "reactivated",
        "closed_after_acceptance",
    }
    assert {status.value for status in APPLICATION_STATUSES} == expected
    assert ApplicationStatus.SENT in APPLICATION_STATUSES
