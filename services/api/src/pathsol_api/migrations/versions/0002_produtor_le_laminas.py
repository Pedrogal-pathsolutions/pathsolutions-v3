"""The test producer reads the slides of its tenant, to build the message from the database (decision 7).

Revision ID: 0002
"""
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute("grant select on slides to pathsol_produtor")
