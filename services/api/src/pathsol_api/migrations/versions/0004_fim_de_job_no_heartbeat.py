"""When a job last reached a terminal state, for the reconciler's start limit (Pedro, 06/11).

The reconciler on VM1 stops starting VM2 after 3 starts in a row in which no
job reached a terminal state. The worker writes the time in the same
transaction as the job's final state; the table still holds no tenant data.

Revision ID: 0004
"""
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.execute("alter table worker_heartbeat add column finished_at timestamptz")
    op.execute("grant update (finished_at) on worker_heartbeat to pathsol_worker")
