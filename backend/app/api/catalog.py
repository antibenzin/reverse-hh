import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.access import NotMemberError, require_membership
from app.domain.applications import can_apply
from app.domain.resume_visibility import can_access_link_only_resume, is_resume_in_catalog
from app.domain.resumes import (
    catalog_card,
    list_catalog_resumes,
    load_resume,
    resume_to_response,
)
from app.models import Company, User, Vacancy
from app.models.enums import VerificationStatus

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _get_verified_company(db: Session, user: User, x_company_id: str | None):
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    company = db.get(Company, company_id)
    if not company or company.is_archived:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="Company not verified")
    return company


@router.get("/resumes")
def search_catalog(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    q: str | None = None,
    city: str | None = None,
):
    company = _get_verified_company(db, user, x_company_id)
    resumes = list_catalog_resumes(db, company=company)
    cards = [catalog_card(resume) for resume in resumes]
    if q:
        needle = q.lower()
        cards = [
            card
            for card in cards
            if needle in (card.get("title") or "").lower()
            or needle in (card.get("desired_role") or "").lower()
        ]
    if city:
        cards = [card for card in cards if card.get("city") == city]
    return cards


@router.get("/resumes/{resume_id}")
def get_catalog_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    token: str | None = Query(default=None),
):
    company = _get_verified_company(db, user, x_company_id)
    resume = load_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if is_resume_in_catalog(resume, company):
        return resume_to_response(resume, employer_view=True)
    if can_access_link_only_resume(resume, company, token=token):
        return resume_to_response(resume, employer_view=True)
    raise HTTPException(status_code=404, detail="Resume not found")


@router.get("/resumes/{resume_id}/can-apply")
def can_apply_endpoint(
    resume_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    company = _get_verified_company(db, user, x_company_id)
    resume = load_resume(db, resume_id)
    vacancy = db.get(Vacancy, vacancy_id)
    if not resume or not vacancy:
        raise HTTPException(status_code=404, detail="Not found")
    result = can_apply(db, company=company, resume=resume, vacancy=vacancy)
    return {
        "can_apply": result.can_apply,
        "warnings": result.warnings,
        "test_required": result.test_required,
    }
