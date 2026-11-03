"""The worker's heartbeat, which the reconciler on VM1 reads (plan 8.3, layer 3).

The table holds no tenant data, neither job nor slide, so reading it needs no
tenant and no BYPASSRLS (plan 19.2, design notes).

Revision ID: 0003
"""
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.execute("""
        create table worker_heartbeat (
            worker text primary key check (worker ~ '^[a-z0-9-]{1,40}$'),
            beat_at timestamptz not null
        )
    """)
    op.execute("grant select, insert, update (beat_at) on worker_heartbeat to pathsol_worker")
