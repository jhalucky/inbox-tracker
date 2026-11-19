"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Asia/Kolkata",
        ),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("telegram_chat_id", name="uq_users_telegram_chat_id"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="gmail"),
        sa.Column("account_email", sa.String(length=320), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("history_cursor", sa.String(length=256), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "account_email", name="uq_accounts_user_email"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("provider_thread_id", sa.String(length=256), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False, server_default=""),
        sa.Column("last_sender", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_message_from_me",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'answered', 'ignored', 'snoozed', 'done')",
            name="ck_threads_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "account_id", "provider_thread_id", name="uq_threads_account_provider"
        ),
    )
    op.create_index("ix_threads_account_id", "threads", ["account_id"])

    op.create_table(
        "classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("needs_reply", sa.Boolean(), nullable=True),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("deadline", sa.String(length=256), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("urgency >= 1 AND urgency <= 5", name="ck_classifications_urgency"),
        sa.CheckConstraint(
            "category IN ('lead', 'client', 'investor', 'hiring', 'internal', "
            "'vendor', 'personal', 'other')",
            name="ck_classifications_category",
        ),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_classifications_thread_id", "classifications", ["thread_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="telegram"),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("telegram_message_id", sa.String(length=64), nullable=True),
        sa.CheckConstraint("channel IN ('telegram')", name="ck_alerts_channel"),
        sa.CheckConstraint("kind IN ('realtime', 'digest')", name="ck_alerts_kind"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_alerts_thread_id", "alerts", ["thread_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "label IN ('not_important', 'mattered', 'done', 'snooze')",
            name="ck_feedback_label",
        ),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_feedback_thread_id", "feedback", ["thread_id"])

    op.create_table(
        "sender_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("importance_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("replies_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reply_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "sender", name="uq_sender_stats_user_sender"),
    )


def downgrade() -> None:
    op.drop_table("sender_stats")
    op.drop_table("feedback")
    op.drop_table("alerts")
    op.drop_table("classifications")
    op.drop_table("threads")
    op.drop_table("accounts")
    op.drop_table("users")
