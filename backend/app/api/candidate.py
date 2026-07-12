from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.candidate_profile import (
    CandidateProfileAlreadyExistsError,
    CandidateProfileNotFoundError,
    create_candidate_profile,
    update_candidate_profile,
)
from app.models import CandidateProfile, User

router = APIRouter(prefix="/candidate", tags=["resumes"])


class CandidateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)


class CandidateProfileResponse(BaseModel):
    id: str
    display_name: str


def _to_response(profile: CandidateProfile) -> CandidateProfileResponse:
    return CandidateProfileResponse(id=str(profile.id), display_name=profile.display_name)


@router.post("/profile", status_code=201, response_model=CandidateProfileResponse)
def create_profile(
    body: CandidateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = create_candidate_profile(db, user_id=user.id, display_name=body.display_name)
    except CandidateProfileAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Candidate profile already exists") from None
    return _to_response(profile)


@router.patch("/profile", response_model=CandidateProfileResponse)
def patch_profile(
    body: CandidateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = update_candidate_profile(db, user_id=user.id, display_name=body.display_name)
    except CandidateProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Candidate profile not found") from None
    return _to_response(profile)
