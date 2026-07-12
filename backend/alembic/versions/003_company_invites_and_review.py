"""Company invites, join requests, manual review flag.

Revision ID: 003
Revises: 002
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invite_status = postgresql.ENUM(
        "pending", "accepted", "revoked", name="invite_status", create_type=False
    )
    join_request_status = postgresql.ENUM(
        "pending", "approved", "rejected", name="join_request_status", create_type=False
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        invite_status.create(bind, checkfirst=True)
        join_request_status.create(bind, checkfirst=True)

    op.add_column(
        "companies",
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("companies", "requires_manual_review", server_default=None)

    op.create_table(
        "company_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_table(
        "company_join_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "user_id", name="uq_company_join_requests_company_user"),
    )


def downgrade() -> None:
    op.drop_table("company_join_requests")
    op.drop_table("company_invites")
    op.drop_column("companies", "requires_manual_review")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="join_request_status").drop(bind, checkfirst=True)
        postgresql.ENUM(name="invite_status").drop(bind, checkfirst=True)
