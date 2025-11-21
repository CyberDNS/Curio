"""add_soft_delete_to_categories

Revision ID: 6571de73a026
Revises: a78d6171b2f2
Create Date: 2025-11-21 20:41:27.832290

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6571de73a026"
down_revision = "a78d6171b2f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_deleted column to categories table
    op.add_column(
        "categories",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("categories", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # Create index on is_deleted for faster queries
    op.create_index(
        op.f("ix_categories_is_deleted"), "categories", ["is_deleted"], unique=False
    )


def downgrade() -> None:
    # Drop index and columns
    op.drop_index(op.f("ix_categories_is_deleted"), table_name="categories")
    op.drop_column("categories", "deleted_at")
    op.drop_column("categories", "is_deleted")
