"""Add tender_release_date column to scrape_runs

This migration adds a proper DATE column to track when tenders were released
(from website header) separately from when they were scraped (run_at).

This enables grouping tenders by release date instead of scrape execution date.

Revision ID: 642bfe5074f2e
Revises: 9d6fa90879e4
Create Date: 2025-11-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '642bfe5074f2e'
down_revision = '9d6fa90879e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add the column (nullable first for safe migration)
    op.add_column('scrape_runs', sa.Column('tender_release_date', sa.Date(), nullable=True))

    # Step 2: Create index before populating (for performance)
    op.create_index(
        'idx_scrape_runs_release_date',
        'scrape_runs',
        ['tender_release_date'],
        unique=False
    )

    # Step 3: Populate the column from date_str
    # This executes raw SQL to parse the date_str format "Day, Mon DD, YYYY"
    op.execute("""
        UPDATE scrape_runs
        SET tender_release_date = TO_DATE(
            SUBSTRING(date_str FROM ',\s*(.+)$'),
            'Mon DD, YYYY'
        )
        WHERE date_str IS NOT NULL
        AND date_str ~ '^\\w+,\\s+\\w+\\s+\\d{1,2},\\s+\\d{4}$'
    """)

    # Step 4: Handle any records that couldn't be parsed - use run_at date
    op.execute("""
        UPDATE scrape_runs
        SET tender_release_date = (run_at AT TIME ZONE 'UTC')::date
        WHERE tender_release_date IS NULL
        AND date_str IS NOT NULL
    """)

    # Step 5: Make column NOT NULL
    op.alter_column('scrape_runs', 'tender_release_date',
                    existing_type=sa.Date(),
                    nullable=False)


def downgrade() -> None:
    # Reverse the changes
    op.drop_index('idx_scrape_runs_release_date', table_name='scrape_runs')
    op.drop_column('scrape_runs', 'tender_release_date')
