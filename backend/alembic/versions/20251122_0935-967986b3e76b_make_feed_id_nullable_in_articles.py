"""make_feed_id_nullable_in_articles

Revision ID: 967986b3e76b
Revises: fac1576058b2
Create Date: 2025-11-22 09:35:48.217730

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '967986b3e76b'
down_revision = 'fac1576058b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make feed_id nullable so articles can remain when feed is deleted
    op.alter_column('articles', 'feed_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Make feed_id non-nullable again
    # Note: This will fail if there are any articles with NULL feed_id
    op.alter_column('articles', 'feed_id',
                    existing_type=sa.Integer(),
                    nullable=False)
