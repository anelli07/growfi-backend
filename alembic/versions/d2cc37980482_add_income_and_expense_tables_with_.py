"""add income and expense tables with relationships

Revision ID: d2cc37980482
Revises: af338e697732
Create Date: 2025-06-22 14:05:59.126084

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "d2cc37980482"
down_revision: Union[str, Sequence[str], None] = "af338e697732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("expense", sa.Column("transaction_date", sa.Date(), nullable=False))
    op.add_column(
        "expense",
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.drop_column("expense", "date")
    op.drop_column("expense", "updated_at")
    op.drop_column("expense", "created_at")
    op.drop_column("expense", "note")
    op.add_column("income", sa.Column("transaction_date", sa.Date(), nullable=False))
    op.add_column(
        "income",
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.drop_column("income", "date")
    op.drop_column("income", "updated_at")
    op.drop_column("income", "created_at")
    op.drop_column("income", "source")
    op.drop_index("ix_user_google_id", table_name="user")
    op.create_index(
        op.f("ix_user_refresh_token"), "user", ["refresh_token"], unique=False
    )
    op.create_unique_constraint(None, "user", ["google_id"])
    op.drop_column("user", "last_reminder_sent")
    op.drop_column("user", "created_at")
    op.drop_column("user", "last_expense_date")
    op.drop_column("user", "last_login")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "user",
        sa.Column(
            "last_login", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "user",
        sa.Column("last_expense_date", sa.DATE(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "last_reminder_sent",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_constraint(None, "user", type_="unique")
    op.drop_index(op.f("ix_user_refresh_token"), table_name="user")
    op.create_index("ix_user_google_id", "user", ["google_id"], unique=False)
    op.add_column(
        "income", sa.Column("source", sa.VARCHAR(), autoincrement=False, nullable=False)
    )
    op.add_column(
        "income",
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "income",
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "income",
        sa.Column("date", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    )
    op.drop_column("income", "description")
    op.drop_column("income", "transaction_date")
    op.add_column(
        "expense", sa.Column("note", sa.VARCHAR(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "expense",
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "expense",
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "expense",
        sa.Column("date", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    )
    op.drop_column("expense", "description")
    op.drop_column("expense", "transaction_date")
    # ### end Alembic commands ###
