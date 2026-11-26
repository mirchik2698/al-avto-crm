"""suppliers and stock lists

Revision ID: 20261123_07
Revises: 20261123_06
Create Date: 2026-11-24

Реестр поставщиков (свой формат прайса, API-ключ, наценка) и история загрузок
остатков. Колонка products.supplier уже существует с ревизии 20261119_04.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_07"
down_revision = "20261123_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(64), nullable=True),
        sa.Column("markup_percent", sa.Numeric(5, 2), nullable=False, server_default=sa.text("25")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"])
    op.create_table(
        "stock_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("filename", sa.String(200), nullable=True),
        sa.Column("rows_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rows_ok", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rows_failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_stock_lists_supplier_id", "stock_lists", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_lists_supplier_id", table_name="stock_lists")
    op.drop_table("stock_lists")
    op.drop_index("ix_suppliers_code", table_name="suppliers")
    op.drop_table("suppliers")
