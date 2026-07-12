"""Candidate profile domain logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import CandidateProfile


class CandidateProfileAlreadyExistsError(Exception):
    pass


class CandidateProfileNotFoundError(Exception):
    pass


def create_candidate_profile(
    db: Session, *, user_id: uuid.UUID, display_name: str
) -> CandidateProfile:
    if db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first():
        raise CandidateProfileAlreadyExistsError()
    profile = CandidateProfile(user_id=user_id, display_name=display_name)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_candidate_profile(
    db: Session, *, user_id: uuid.UUID, display_name: str
) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if not profile:
        raise CandidateProfileNotFoundError()
    profile.display_name = display_name
    db.commit()
    db.refresh(profile)
    return profile
