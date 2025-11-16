"""add_category_descriptions_and_duplicate_detection

Revision ID: 3fa2ef5c5685
Revises: 739f10864c56
Create Date: 2025-11-19 05:19:55.487408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3fa2ef5c5685'
down_revision = '739f10864c56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description field to categories table
    op.add_column('categories', sa.Column('description', sa.String(), nullable=True))

    # Add duplicate detection fields to articles table
    op.add_column('articles', sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('articles', sa.Column('duplicate_of_id', sa.Integer(), nullable=True))

    # Create foreign key for duplicate_of_id
    op.create_foreign_key(
        'fk_articles_duplicate_of_id',
        'articles',
        'articles',
        ['duplicate_of_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Try to enable pgvector extension and create vector column
    # If pgvector is not installed, add as TEXT column instead (will be converted later)
    conn = op.get_bind()

    # Check if pgvector is available
    pgvector_available = False
    try:
        result = conn.execute(sa.text(
            "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
        ))
        pgvector_available = result.fetchone() is not None
    except Exception as e:
        print(f"⚠ Could not check for pgvector availability: {e}")
        pgvector_available = False

    if pgvector_available:
        try:
            # Try to create pgvector extension
            conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS vector'))

            # Add vector column
            op.add_column('articles', sa.Column('title_embedding', sa.String(), nullable=True))

            # Convert to vector type
            conn.execute(sa.text('ALTER TABLE articles ALTER COLUMN title_embedding TYPE vector(1536) USING title_embedding::vector(1536)'))

            # Create vector index
            conn.execute(sa.text('CREATE INDEX idx_articles_title_embedding ON articles USING ivfflat (title_embedding vector_cosine_ops) WITH (lists = 100)'))

            print("✓ pgvector extension installed and vector column created")
        except Exception as e:
            print(f"⚠ Failed to set up pgvector: {e}")
            print("⚠ Adding title_embedding as TEXT column instead")

            # Add as TEXT column if pgvector setup failed
            try:
                op.add_column('articles', sa.Column('title_embedding', sa.Text(), nullable=True))
            except:
                # Column might already exist from failed attempt above
                pass
    else:
        print("⚠ pgvector extension not available in this PostgreSQL installation")
        print("⚠ Adding title_embedding as TEXT column instead")
        print("⚠ To enable vector similarity search, install pgvector and run migration again")

        # Add as TEXT column if pgvector is not available
        op.add_column('articles', sa.Column('title_embedding', sa.Text(), nullable=True))

    # Remove tags column from articles table (deprecated in favor of categories)
    op.drop_column('articles', 'tags')


def downgrade() -> None:
    # Restore tags column
    op.add_column('articles', sa.Column('tags', sa.JSON(), nullable=True))

    # Drop vector index
    op.execute('DROP INDEX IF EXISTS idx_articles_title_embedding')

    # Drop duplicate detection columns
    op.drop_constraint('fk_articles_duplicate_of_id', 'articles', type_='foreignkey')
    op.drop_column('articles', 'title_embedding')
    op.drop_column('articles', 'duplicate_of_id')
    op.drop_column('articles', 'is_duplicate')

    # Drop category description
    op.drop_column('categories', 'description')

    # Note: Not dropping pgvector extension in case other tables use it
