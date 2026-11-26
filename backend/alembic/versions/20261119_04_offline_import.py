"""Add offline retry keys and product supplier."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_04"
down_revision = "20261119_03"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("clients", "orders"):
        op.add_column(table, sa.Column("sync_key", sa.String(80), nullable=True))
        op.create_unique_constraint(f"uq_{table}_sync_key", table, ["sync_key"])
    op.add_column("products", sa.Column("supplier", sa.String(120), nullable=True))


def downgrade():
    raise NotImplementedError("Downgrade would remove supplier information and offline retry keys")
