"""Application state machine — implement in Applications epic."""

APPLICATION_STATUSES = frozenset({
    "sent",
    "viewed",
    "accepted",
    "rejected",
    "auto_rejected",
    "expired",
    "reactivation_requested",
    "reactivated",
    "closed_after_acceptance",
})
