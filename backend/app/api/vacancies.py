import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.access import AccessDeniedError
from app.domain.vacancies import (
    VacancyNotFoundError,
    VacancyValidationError,
    assign_recruiters,
    create_vacancy,
    list_vacancies,
    set_vacancy_status,
    update_vacancy,
    vacancy_to_info,
)
from app.models import User
from app.models.enums import VacancyStatus

router = APIRouter(prefix="/companies/{company_id}/vacancies", tags=["vacancies"])


class VacancyCreateRequest(BaseModel):
    data: dict = Field(default_factory=dict)


class VacancyUpdateRequest(BaseModel):
    data: dict


class VacancyStatusRequest(BaseModel):
    status: VacancyStatus


class AssignRecruitersRequest(BaseModel):
    recruiter_ids: list[uuid.UUID]


def _to_response(info) -> dict:
    return {
        "id": info.id,
        "company_id": info.company_id,
        "status": info.status.value,
        "created_by": info.created_by,
        "data": info.data,
        "recruiter_ids": info.recruiter_ids,
    }


@router.get("")
def list_company_vacancies(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        vacancies = list_vacancies(db, user=user, company_id=company_id)
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    return [_to_response(v) for v in vacancies]


@router.post("", status_code=201)
def create_company_vacancy(
    company_id: uuid.UUID,
    body: VacancyCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        vacancy = create_vacancy(db, user=user, company_id=company_id, data=body.data)
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    return _to_response(vacancy_to_info(vacancy))


@router.patch("/{vacancy_id}")
def patch_vacancy(
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    body: VacancyUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        vacancy = update_vacancy(
            db, user=user, company_id=company_id, vacancy_id=vacancy_id, data=body.data
        )
    except VacancyNotFoundError:
        raise HTTPException(status_code=404, detail="Vacancy not found") from None
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Cannot edit vacancy") from None
    return _to_response(vacancy_to_info(vacancy))


@router.post("/{vacancy_id}/status")
def post_vacancy_status(
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    body: VacancyStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        vacancy = set_vacancy_status(
            db,
            user=user,
            company_id=company_id,
            vacancy_id=vacancy_id,
            status=body.status,
        )
    except VacancyNotFoundError:
        raise HTTPException(status_code=404, detail="Vacancy not found") from None
    except VacancyValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Cannot change vacancy status") from None
    return _to_response(vacancy_to_info(vacancy))


@router.post("/{vacancy_id}/recruiters")
def post_vacancy_recruiters(
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    body: AssignRecruitersRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        vacancy = assign_recruiters(
            db,
            user=user,
            company_id=company_id,
            vacancy_id=vacancy_id,
            recruiter_ids=body.recruiter_ids,
        )
    except VacancyNotFoundError:
        raise HTTPException(status_code=404, detail="Vacancy not found") from None
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Cannot assign recruiters") from None
    return _to_response(vacancy_to_info(vacancy))
