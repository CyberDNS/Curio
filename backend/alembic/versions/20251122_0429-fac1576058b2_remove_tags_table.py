"""remove_tags_table

Revision ID: fac1576058b2
Revises: 6571de73a026
Create Date: 2025-11-22 04:29:39.238833

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fac1576058b2"
down_revision = "6571de73a026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop tags table and its indexes
    op.drop_index("idx_user_tag_name", table_name="tags")
    op.drop_table("tags")


def downgrade() -> None:
    # Recreate tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_id"), "tags", ["id"], unique=False)
    op.create_index(op.f("ix_tags_user_id"), "tags", ["user_id"], unique=False)
    op.create_index("idx_user_tag_name", "tags", ["user_id", "name"], unique=True)
