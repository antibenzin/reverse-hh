from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import VacancyStatus
from app.models.types import sa_enum

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.company import Company


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    status: Mapped[VacancyStatus] = mapped_column(
        sa_enum(VacancyStatus, "vacancy_status"),
        default=VacancyStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    data: Mapped[dict | None] = mapped_column(JSON)

    company: Mapped[Company] = relationship(back_populates="vacancies")
    recruiters: Mapped[list[VacancyRecruiter]] = relationship(back_populates="vacancy")
    applications: Mapped[list[Application]] = relationship(back_populates="vacancy")


class VacancyRecruiter(Base):
    __tablename__ = "vacancy_recruiters"

    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vacancies.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )

    vacancy: Mapped[Vacancy] = relationship(back_populates="recruiters")

