import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.access import AccessDeniedError, NotMemberError, require_membership
from app.domain.companies import (
    AlreadyMemberError,
    CompanyNotFoundError,
    DuplicateJoinRequestError,
    InviteNotFoundError,
    JoinRequestNotFoundError,
    accept_invite,
    approve_join_request,
    archive_company,
    company_to_info,
    create_company,
    create_join_request,
    get_company_for_member,
    invite_recruiter,
    list_members,
    list_user_companies,
    submit_verification,
    update_company,
)
from app.models import User
from app.models.enums import CompanyMemberRole, VerificationStatus

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str | None = None
    tax_id: str | None = None


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = None
    tax_id: str | None = None
    profile_data: dict | None = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    website: str | None
    tax_id: str | None
    verification_status: VerificationStatus
    is_archived: bool
    requires_manual_review: bool
    profile_data: dict | None
    my_role: CompanyMemberRole | None = None


class MemberResponse(BaseModel):
    user_id: str
    email: str
    role: CompanyMemberRole


class InviteRequest(BaseModel):
    email: EmailStr


class InviteResponse(BaseModel):
    id: str
    email: str
    token: str


class JoinRequestResponse(BaseModel):
    id: str
    user_id: str
    status: str


class AcceptInviteRequest(BaseModel):
    token: str


def _company_response(company, role: CompanyMemberRole | None = None) -> CompanyResponse:
    info = company_to_info(company, role=role)
    return CompanyResponse(**info.__dict__)


@router.get("", response_model=list[CompanyResponse])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_company_response_from_info(c) for c in list_user_companies(db, user)]


def _company_response_from_info(info) -> CompanyResponse:
    return CompanyResponse(**info.__dict__)


@router.post("", status_code=201, response_model=CompanyResponse)
def create_company_endpoint(
    body: CompanyCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = create_company(
        db,
        user=user,
        name=body.name,
        website=body.website,
        tax_id=body.tax_id,
    )
    return _company_response(company, role=CompanyMemberRole.OWNER)


@router.post("/invites/accept", status_code=200)
def accept_invite_endpoint(
    body: AcceptInviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        accept_invite(db, user=user, token=body.token)
    except InviteNotFoundError:
        raise HTTPException(status_code=404, detail="Invite not found") from None
    except AlreadyMemberError:
        raise HTTPException(status_code=400, detail="User is already a member") from None
    return {"ok": True}


@router.get("/workspace/me", response_model=MemberResponse)
def workspace_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    user_row = db.get(User, membership.user_id)
    return MemberResponse(
        user_id=str(membership.user_id), email=user_row.email, role=membership.role
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        company, membership = get_company_for_member(db, user=user, company_id=company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    return _company_response(company, role=membership.role)


@router.patch("/{company_id}", response_model=CompanyResponse)
def patch_company(
    company_id: uuid.UUID,
    body: CompanyUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        company = update_company(
            db,
            user=user,
            company_id=company_id,
            name=body.name,
            website=body.website,
            tax_id=body.tax_id,
            profile_data=body.profile_data,
        )
        membership = get_company_for_member(db, user=user, company_id=company_id)[1]
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except (AccessDeniedError,):
        raise HTTPException(status_code=403, detail="Owner role required") from None
    return _company_response(company, role=membership.role)


@router.post("/{company_id}/archive", status_code=204)
def archive_company_endpoint(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        archive_company(db, user=user, company_id=company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except (AccessDeniedError,):
        raise HTTPException(status_code=403, detail="Owner role required") from None
    return None


@router.post("/{company_id}/verify", status_code=202, response_model=CompanyResponse)
def verify_company(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        company = submit_verification(db, user=user, company_id=company_id)
        membership = get_company_for_member(db, user=user, company_id=company_id)[1]
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except (AccessDeniedError,):
        raise HTTPException(status_code=403, detail="Owner role required") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _company_response(company, role=membership.role)


@router.get("/{company_id}/members", response_model=list[MemberResponse])
def get_members(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        members = list_members(db, user=user, company_id=company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    return [MemberResponse(**m.__dict__) for m in members]


@router.post("/{company_id}/members", status_code=201, response_model=InviteResponse)
def invite_member(
    company_id: uuid.UUID,
    body: InviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        invite = invite_recruiter(db, user=user, company_id=company_id, email=body.email)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except (AccessDeniedError,):
        raise HTTPException(status_code=403, detail="Owner role required") from None
    except AlreadyMemberError:
        raise HTTPException(status_code=400, detail="User is already a member") from None
    return InviteResponse(id=str(invite.id), email=invite.email, token=invite.token)


@router.post("/{company_id}/join-requests", status_code=201, response_model=JoinRequestResponse)
def request_join(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        request = create_join_request(db, user=user, company_id=company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except AlreadyMemberError:
        raise HTTPException(status_code=400, detail="User is already a member") from None
    except DuplicateJoinRequestError:
        raise HTTPException(status_code=400, detail="Join request already pending") from None
    return JoinRequestResponse(
        id=str(request.id), user_id=str(request.user_id), status=request.status.value
    )


@router.post(
    "/{company_id}/join-requests/{request_id}/approve",
    status_code=200,
    response_model=MemberResponse,
)
def approve_join(
    company_id: uuid.UUID,
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        member = approve_join_request(
            db, user=user, company_id=company_id, request_id=request_id
        )
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except JoinRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Join request not found") from None
    except (AccessDeniedError,):
        raise HTTPException(status_code=403, detail="Owner role required") from None
    except AlreadyMemberError:
        raise HTTPException(status_code=400, detail="User is already a member") from None
    user_row = db.get(User, member.user_id)
    return MemberResponse(
        user_id=str(member.user_id), email=user_row.email, role=member.role
    )
