import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.resumes import (
    CandidateProfileRequiredError,
    CompanyAlreadyBlockedError,
    ContactInput,
    ResumeNotFoundError,
    ResumePublishError,
    VisibilityRuleInput,
    WorkExperienceInput,
    archive_resume,
    block_company,
    create_resume,
    delete_resume_permanently,
    get_resume_for_owner,
    list_own_resumes,
    publish_resume,
    resume_to_response,
    update_resume_draft,
)
from app.models import User
from app.models.enums import ContactType, ResumeVisibility, VisibilityRuleType

router = APIRouter(prefix="/resumes", tags=["resumes"])


class ContactSchema(BaseModel):
    type: ContactType
    value: str = Field(min_length=1, max_length=255)
    is_public: bool = False


class WorkExperienceSchema(BaseModel):
    company_name: str | None = None
    is_nda: bool = False
    role: str = Field(min_length=1, max_length=255)
    started_at: date
    ended_at: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    industry_id: uuid.UUID | None = None
    skills: list[str] | None = None


class VisibilityRuleSchema(BaseModel):
    rule_type: VisibilityRuleType
    rule_value: str = Field(min_length=1, max_length=255)


class ResumeCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ResumeUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    visibility: ResumeVisibility | None = None
    cover_letter_required: bool | None = None
    auto_reject_settings: dict | None = None
    draft_data: dict | None = None
    contacts: list[ContactSchema] | None = None
    work_experiences: list[WorkExperienceSchema] | None = None
    visibility_rules: list[VisibilityRuleSchema] | None = None


class BlockCompanyRequest(BaseModel):
    company_id: uuid.UUID


def _map_contacts(items: list[ContactSchema] | None) -> list[ContactInput] | None:
    if items is None:
        return None
    return [
        ContactInput(type=item.type, value=item.value, is_public=item.is_public)
        for item in items
    ]


def _map_experiences(items: list[WorkExperienceSchema] | None) -> list[WorkExperienceInput] | None:
    if items is None:
        return None
    return [
        WorkExperienceInput(
            company_name=item.company_name,
            is_nda=item.is_nda,
            role=item.role,
            started_at=item.started_at,
            ended_at=item.ended_at,
            description=item.description,
            industry_id=item.industry_id,
            skills=item.skills,
        )
        for item in items
    ]


def _map_rules(items: list[VisibilityRuleSchema] | None) -> list[VisibilityRuleInput] | None:
    if items is None:
        return None
    return [
        VisibilityRuleInput(rule_type=item.rule_type, rule_value=item.rule_value)
        for item in items
    ]


def _handle_resume_errors(exc: Exception) -> None:
    if isinstance(exc, CandidateProfileRequiredError):
        raise HTTPException(status_code=400, detail="Candidate profile required") from None
    if isinstance(exc, ResumeNotFoundError):
        raise HTTPException(status_code=404, detail="Resume not found") from None
    raise exc


@router.get("")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        resumes = list_own_resumes(db, user)
    except CandidateProfileRequiredError:
        raise HTTPException(status_code=400, detail="Candidate profile required") from None
    return [resume_to_response(resume) for resume in resumes]


@router.post("", status_code=201)
def create_resume_endpoint(
    body: ResumeCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resume = create_resume(db, user=user, title=body.title)
    except CandidateProfileRequiredError:
        raise HTTPException(status_code=400, detail="Candidate profile required") from None
    return resume_to_response(resume)


@router.get("/{resume_id}")
def get_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    except Exception as exc:
        _handle_resume_errors(exc)
    return resume_to_response(resume)


@router.patch("/{resume_id}")
def patch_resume(
    resume_id: uuid.UUID,
    body: ResumeUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resume = update_resume_draft(
            db,
            user=user,
            resume_id=resume_id,
            title=body.title,
            visibility=body.visibility,
            cover_letter_required=body.cover_letter_required,
            auto_reject_settings=body.auto_reject_settings,
            draft_data=body.draft_data,
            contacts=_map_contacts(body.contacts),
            work_experiences=_map_experiences(body.work_experiences),
            visibility_rules=_map_rules(body.visibility_rules),
        )
    except Exception as exc:
        _handle_resume_errors(exc)
    return resume_to_response(resume)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(
    resume_id: uuid.UUID,
    permanent: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if permanent:
            delete_resume_permanently(db, user=user, resume_id=resume_id)
        else:
            archive_resume(db, user=user, resume_id=resume_id)
    except Exception as exc:
        _handle_resume_errors(exc)
    return None


@router.post("/{resume_id}/publish")
def publish_resume_endpoint(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resume = publish_resume(db, user=user, resume_id=resume_id)
    except ResumePublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        _handle_resume_errors(exc)
    return resume_to_response(resume)


@router.post("/{resume_id}/block-company", status_code=204)
def block_company_endpoint(
    resume_id: uuid.UUID,
    body: BlockCompanyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        block_company(db, user=user, resume_id=resume_id, company_id=body.company_id)
    except CompanyAlreadyBlockedError:
        raise HTTPException(status_code=400, detail="Company already blocked") from None
    except Exception as exc:
        _handle_resume_errors(exc)
    return None
