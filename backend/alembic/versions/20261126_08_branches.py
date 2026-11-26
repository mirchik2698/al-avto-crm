"""branches: two filials, branch scoping for users/clients/orders

Revision ID: 20261126_08
Revises: 20261123_07
Create Date: 2026-11-26

Филиалы «Дискотека» и «АлАвто». Существующие сотрудники и клиенты относятся
к филиалу «АлАвто»; заказы помечаются по филиалу создателя/клиента.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261126_08"
down_revision = "20261123_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    branches = op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
    )
    op.bulk_insert(branches, [
        {"id": 1, "name": "АлАвто", "code": "alavto"},
        {"id": 2, "name": "Дискотека", "code": "diskoteka"},
    ])
    op.add_column("users", sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True))
    op.create_index("ix_users_branch_id", "users", ["branch_id"])
    op.add_column("clients", sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False, server_default="1"))
    op.create_index("ix_clients_branch_id", "clients", ["branch_id"])
    op.add_column("orders", sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False, server_default="1"))
    op.create_index("ix_orders_branch_id", "orders", ["branch_id"])
    # Сотрудники (не админы) — в филиал «АлАвто»
    op.execute("UPDATE users SET branch_id = 1 WHERE role = 'employee'")
    op.alter_column("clients", "branch_id", server_default=None)
    op.alter_column("orders", "branch_id", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_orders_branch_id", table_name="orders")
    op.drop_column("orders", "branch_id")
    op.drop_index("ix_clients_branch_id", table_name="clients")
    op.drop_column("clients", "branch_id")
    op.drop_index("ix_users_branch_id", table_name="users")
    op.drop_column("users", "branch_id")
    op.drop_table("branches")
