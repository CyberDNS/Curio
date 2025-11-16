"""remove_is_selected_column

Revision ID: 702e5406f54f
Revises: 425f1b0ff751
Create Date: 2025-11-18 05:14:10.535767

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '702e5406f54f'
down_revision = '425f1b0ff751'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the is_selected column - we'll use relevance_score >= 0.6 instead
    op.drop_column('articles', 'is_selected')


def downgrade() -> None:
    # Restore is_selected column if needed
    op.add_column('articles', sa.Column('is_selected', sa.Boolean(), server_default='false', nullable=True))
