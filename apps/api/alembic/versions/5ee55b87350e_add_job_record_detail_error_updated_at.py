"""add job record detail error updated_at

Revision ID: 5ee55b87350e
Revises: 41b7146f7d8a
Create Date: 2026-09-18 19:40:02.310852

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5ee55b87350e'
down_revision: str | Sequence[str] | None = '41b7146f7d8a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_records", sa.Column("detail", sa.Text(), nullable=True))
    op.add_column("job_records", sa.Column("error", sa.Text(), nullable=True))
    op.add_column("job_records", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("job_records", "updated_at")
    op.drop_column("job_records", "error")
    op.drop_column("job_records", "detail")