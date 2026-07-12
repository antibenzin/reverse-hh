"""PostgreSQL enum types and catalog indexes.

Revision ID: 002
Revises: 001
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUMS: dict[str, list[str]] = {
    "resume_status": ["draft", "published", "archived", "deleted"],
    "resume_visibility": ["public", "link_only", "hidden"],
    "contact_type": ["phone", "email", "telegram", "linkedin", "website", "other"],
    "visibility_rule_type": ["hide_company_id", "hide_domain", "hide_tax_id"],
    "verification_status": ["pending", "verified", "rejected", "suspended"],
    "company_member_role": ["owner", "recruiter"],
    "vacancy_status": ["draft", "active", "archived"],
    "application_status": [
        "sent",
        "viewed",
        "accepted",
        "rejected",
        "auto_rejected",
        "expired",
        "reactivation_requested",
        "reactivated",
        "closed_after_acceptance",
    ],
    "question_type": ["single_choice", "multi_choice", "text", "scale"],
    "complaint_target_type": ["company", "message", "application", "resume"],
    "complaint_status": ["open", "resolved", "dismissed"],
}


def _create_pg_enums() -> dict[str, postgresql.ENUM]:
    bind = op.get_bind()
    enums: dict[str, postgresql.ENUM] = {}
    for name, values in _ENUMS.items():
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(bind, checkfirst=True)
        enums[name] = enum_type
    return enums


def _alter_to_enum(table: str, column: str, enum_name: str, enums: dict[str, postgresql.ENUM]) -> None:
    op.alter_column(
        table,
        column,
        type_=enums[enum_name],
        postgresql_using=f"{column}::{enum_name}",
    )


def upgrade() -> None:
    enums = _create_pg_enums()

    _alter_to_enum("resumes", "status", "resume_status", enums)
    _alter_to_enum("resumes", "visibility", "resume_visibility", enums)
    _alter_to_enum("resume_contacts", "type", "contact_type", enums)
    _alter_to_enum("resume_visibility_rules", "rule_type", "visibility_rule_type", enums)
    _alter_to_enum("companies", "verification_status", "verification_status", enums)
    _alter_to_enum("company_members", "role", "company_member_role", enums)
    _alter_to_enum("vacancies", "status", "vacancy_status", enums)
    _alter_to_enum("applications", "status", "application_status", enums)
    _alter_to_enum("test_questions", "type", "question_type", enums)
    _alter_to_enum("complaints", "target_type", "complaint_target_type", enums)
    _alter_to_enum("complaints", "status", "complaint_status", enums)

    op.alter_column(
        "resumes",
        "published_data",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="published_data::jsonb",
    )
    op.alter_column(
        "resumes",
        "draft_data",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="draft_data::jsonb",
    )

    op.alter_column(
        "application_test_answers",
        "answer_options",
        type_=postgresql.ARRAY(sa.Uuid()),
        postgresql_using=(
            "CASE WHEN answer_options IS NULL THEN NULL::uuid[] "
            "ELSE ARRAY(SELECT json_array_elements_text(answer_options))::uuid[] END"
        ),
    )

    op.create_index(
        "ix_resumes_published_data_skills_gin",
        "resumes",
        [sa.text("(published_data->'skills')")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_resumes_published_salary_min",
        "resumes",
        [sa.text("(published_data->>'salary_min')")],
    )
    op.create_index(
        "ix_resumes_published_salary_max",
        "resumes",
        [sa.text("(published_data->>'salary_max')")],
    )
    op.create_index(
        "ix_resumes_catalog_filters",
        "resumes",
        [
            sa.text("(published_data->>'industry_id')"),
            sa.text("(published_data->>'city')"),
            sa.text("(published_data->'work_formats')"),
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_resumes_catalog_filters", table_name="resumes")
    op.drop_index("ix_resumes_published_salary_max", table_name="resumes")
    op.drop_index("ix_resumes_published_salary_min", table_name="resumes")
    op.drop_index("ix_resumes_published_data_skills_gin", table_name="resumes")

    op.alter_column(
        "application_test_answers",
        "answer_options",
        type_=sa.JSON(),
        postgresql_using="to_json(answer_options)",
    )
    op.alter_column("resumes", "draft_data", type_=sa.JSON(), postgresql_using="draft_data::json")
    op.alter_column(
        "resumes",
        "published_data",
        type_=sa.JSON(),
        postgresql_using="published_data::json",
    )

    op.alter_column("complaints", "status", type_=sa.String(length=32))
    op.alter_column("complaints", "target_type", type_=sa.String(length=32))
    op.alter_column("test_questions", "type", type_=sa.String(length=32))
    op.alter_column("applications", "status", type_=sa.String(length=64))
    op.alter_column("vacancies", "status", type_=sa.String(length=32))
    op.alter_column("company_members", "role", type_=sa.String(length=32))
    op.alter_column("companies", "verification_status", type_=sa.String(length=32))
    op.alter_column("resume_visibility_rules", "rule_type", type_=sa.String(length=32))
    op.alter_column("resume_contacts", "type", type_=sa.String(length=32))
    op.alter_column("resumes", "visibility", type_=sa.String(length=32))
    op.alter_column("resumes", "status", type_=sa.String(length=32))

    bind = op.get_bind()
    for name in reversed(list(_ENUMS.keys())):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
