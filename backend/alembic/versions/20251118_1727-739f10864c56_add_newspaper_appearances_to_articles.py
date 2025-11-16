"""add_newspaper_appearances_to_articles

Revision ID: 739f10864c56
Revises: 702e5406f54f
Create Date: 2025-11-18 17:27:07.579411

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '739f10864c56'
down_revision = '702e5406f54f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add newspaper_appearances JSONB column to track which newspaper editions an article appeared in
    # Format: {"2025-01-15": "today", "2025-01-16": "technology"}
    op.add_column('articles', sa.Column('newspaper_appearances', sa.JSON(), nullable=True))

    # Set default empty dict for existing articles
    op.execute("UPDATE articles SET newspaper_appearances = '{}'::jsonb WHERE newspaper_appearances IS NULL")


def downgrade() -> None:
    # Remove newspaper_appearances column if needed
    op.drop_column('articles', 'newspaper_appearances')
