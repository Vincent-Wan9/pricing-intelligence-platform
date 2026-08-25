"""support queued crawl jobs and active-job uniqueness

Revision ID: d4e5f6a7b8c9
Revises: c7a8d9e0f1b2
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c7a8d9e0f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("crawl_jobs", "started_at", nullable=True)
    # Preserve the newest active job if historical data already contains duplicates.
    op.execute("""
        WITH duplicates AS (
            SELECT job_id,
                   row_number() OVER (
                       PARTITION BY competitor_id
                       ORDER BY started_at DESC NULLS LAST, job_id DESC
                   ) AS position
            FROM crawl_jobs
            WHERE status IN ('pending', 'running')
        )
        UPDATE crawl_jobs
        SET status = 'failed',
            completed_at = CURRENT_TIMESTAMP,
            error_message = 'Superseded while enabling active-job uniqueness'
        WHERE job_id IN (SELECT job_id FROM duplicates WHERE position > 1)
    """)
    op.create_index(
        "uq_crawl_jobs_active_competitor",
        "crawl_jobs",
        ["competitor_id"],
        unique=True,
        postgresql_where="status IN ('pending', 'running')",
    )


def downgrade() -> None:
    op.drop_index("uq_crawl_jobs_active_competitor", table_name="crawl_jobs")
    op.execute("UPDATE crawl_jobs SET started_at = CURRENT_TIMESTAMP WHERE started_at IS NULL")
    op.alter_column("crawl_jobs", "started_at", nullable=False)
