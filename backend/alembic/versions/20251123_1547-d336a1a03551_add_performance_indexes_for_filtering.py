"""add_performance_indexes_for_filtering

Revision ID: d336a1a03551
Revises: 967986b3e76b
Create Date: 2025-11-23 15:47:02.410998

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d336a1a03551"
down_revision = "967986b3e76b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for commonly filtered columns
    op.create_index(
        "ix_articles_published_date", "articles", ["published_date"], unique=False
    )
    op.create_index(
        "ix_articles_category_id", "articles", ["category_id"], unique=False
    )
    op.create_index("ix_articles_feed_id", "articles", ["feed_id"], unique=False)

    # Composite index for common query patterns
    op.create_index(
        "ix_articles_user_published",
        "articles",
        ["user_id", "published_date"],
        unique=False,
    )
    op.create_index(
        "ix_articles_user_category",
        "articles",
        ["user_id", "category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_articles_user_category", table_name="articles")
    op.drop_index("ix_articles_user_published", table_name="articles")
    op.drop_index("ix_articles_feed_id", table_name="articles")
    op.drop_index("ix_articles_category_id", table_name="articles")
    op.drop_index("ix_articles_published_date", table_name="articles")
