"""Application state machine — implement in Applications epic."""

from app.models.enums import ApplicationStatus

APPLICATION_STATUSES = frozenset(ApplicationStatus)
