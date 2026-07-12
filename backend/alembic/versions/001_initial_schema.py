"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "industries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "specializations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=512), nullable=True),
        sa.Column("tax_id", sa.String(length=64), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("profile_data", sa.JSON(), nullable=True),
        sa.Column("application_limit_monthly", sa.Integer(), nullable=False),
        sa.Column("applications_used_this_month", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "industries_pending",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "specializations_pending",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "skills_pending",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "company_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "user_id", name="uq_company_members_company_user"),
    )
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("link_token", sa.String(length=64), nullable=True),
        sa.Column("published_data", sa.JSON(), nullable=True),
        sa.Column("draft_data", sa.JSON(), nullable=True),
        sa.Column("cover_letter_required", sa.Boolean(), nullable=False),
        sa.Column("auto_reject_settings", sa.JSON(), nullable=True),
        sa.Column("test_editing", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("link_token"),
    )
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=512), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resume_work_experiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("is_nda", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry_id", sa.Uuid(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resume_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resume_visibility_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("rule_value", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resume_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id"),
    )
    op.create_table(
        "vacancy_recruiters",
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"]),
        sa.PrimaryKeyConstraint("vacancy_id", "user_id"),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("sent_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("resume_snapshot", sa.JSON(), nullable=False),
        sa.Column("vacancy_snapshot", sa.JSON(), nullable=False),
        sa.Column("test_snapshot", sa.JSON(), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("rejection_reasons", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("employer_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extended_once", sa.Boolean(), nullable=False),
        sa.Column("limit_debited", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id", "vacancy_id", name="uq_applications_resume_vacancy"),
    )
    op.create_table(
        "saved_resumes",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("saved_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["saved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("company_id", "resume_id"),
    )
    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("complaint_id", sa.Uuid(), nullable=True),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("hint", sa.String(length=1000), nullable=True),
        sa.Column("scale_min", sa.Integer(), nullable=True),
        sa.Column("scale_max", sa.Integer(), nullable=True),
        sa.Column("expected_scale_min", sa.Integer(), nullable=True),
        sa.Column("expected_scale_max", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("is_read_only", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
    )
    op.create_table(
        "application_test_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_options", sa.JSON(), nullable=True),
        sa.Column("answer_scale", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_question_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("is_expected", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["test_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_resumes_status_visibility",
        "resumes",
        ["status", "visibility"],
        postgresql_where=sa.text("status = 'published'"),
    )
    op.create_index("ix_applications_resume_id_status", "applications", ["resume_id", "status"])
    op.create_index("ix_applications_company_id_status", "applications", ["company_id", "status"])
    op.create_index("ix_applications_sent_by", "applications", ["sent_by"])
    op.create_index("ix_vacancies_company_id_status", "vacancies", ["company_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_vacancies_company_id_status", table_name="vacancies")
    op.drop_index("ix_applications_sent_by", table_name="applications")
    op.drop_index("ix_applications_company_id_status", table_name="applications")
    op.drop_index("ix_applications_resume_id_status", table_name="applications")
    op.drop_index("ix_resumes_status_visibility", table_name="resumes")
    op.drop_table("chat_messages")
    op.drop_table("test_question_options")
    op.drop_table("application_test_answers")
    op.drop_table("chats")
    op.drop_table("test_questions")
    op.drop_table("moderation_actions")
    op.drop_table("saved_resumes")
    op.drop_table("applications")
    op.drop_table("vacancy_recruiters")
    op.drop_table("tests")
    op.drop_table("resume_blocks")
    op.drop_table("resume_visibility_rules")
    op.drop_table("resume_contacts")
    op.drop_table("resume_work_experiences")
    op.drop_table("audit_events")
    op.drop_table("notifications")
    op.drop_table("complaints")
    op.drop_table("vacancies")
    op.drop_table("resumes")
    op.drop_table("company_members")
    op.drop_table("skills_pending")
    op.drop_table("specializations_pending")
    op.drop_table("industries_pending")
    op.drop_table("companies")
    op.drop_table("candidate_profiles")
    op.drop_table("skills")
    op.drop_table("specializations")
    op.drop_table("industries")
    op.drop_table("users")
