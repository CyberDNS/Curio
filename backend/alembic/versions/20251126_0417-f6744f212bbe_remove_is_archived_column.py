"""remove_is_archived_column

Revision ID: f6744f212bbe
Revises: 3bda1b05f6bf
Create Date: 2025-11-26 04:17:47.890028

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f6744f212bbe"
down_revision = "3bda1b05f6bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove is_archived column from articles table
    op.drop_column("articles", "is_archived")


def downgrade() -> None:
    # Add back is_archived column if needed to rollback
    op.add_column(
        "articles",
        sa.Column("is_archived", sa.Boolean(), nullable=True, server_default="false"),
    )
