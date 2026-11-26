"""order statuses and client codes

Revision ID: 20261123_05
Revises: 20261119_04
Create Date: 2026-11-23

Заказы: пять статусов схлопываются в два — «В пути» (по умолчанию) и «Завершён».
Клиенты: появляется человекочитаемый ID = имя + последние четыре цифры телефона.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261123_05"
down_revision = "20261119_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("clients", sa.Column("code", sa.String(40), nullable=True))
    op.execute("""
        WITH base AS (
            SELECT id, btrim(name) AS name, regexp_replace(phone, '\\D', '', 'g') AS digits
            FROM clients
        ), codes AS (
            SELECT id, name || COALESCE(right(digits, 4), '') AS code FROM base
        ), ranked AS (
            SELECT id, code, row_number() OVER (PARTITION BY code ORDER BY id) AS position
            FROM codes
        )
        UPDATE clients
        SET code = CASE WHEN ranked.position = 1 THEN ranked.code ELSE ranked.code || '-' || ranked.position END
        FROM ranked
        WHERE clients.id = ranked.id
    """)
    op.alter_column("clients", "code", existing_type=sa.String(40), nullable=False)
    op.create_index("ix_clients_code", "clients", ["code"], unique=True)

    op.alter_column(
        "orders", "status",
        existing_type=postgresql.ENUM("new", "in_progress", "ready", "completed", "cancelled",
                                      name="orderstatus", create_type=False),
        type_=sa.String(20), existing_nullable=False, postgresql_using="status::text",
    )
    op.execute("UPDATE orders SET status = CASE WHEN status = 'completed' THEN 'completed' ELSE 'in_transit' END")
    op.create_check_constraint("ck_orders_status", "orders", "status IN ('in_transit', 'completed')")
    op.create_index("ix_orders_status", "orders", ["status"])
    postgresql.ENUM(name="orderstatus").drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    order_status = postgresql.ENUM("new", "in_progress", "ready", "completed", "cancelled",
                                   name="orderstatus", create_type=False)
    order_status.create(bind, checkfirst=True)
    op.alter_column("orders", "status", existing_type=sa.String(20), type_=order_status,
                    existing_nullable=False, postgresql_using="status::text::orderstatus")
    op.execute("UPDATE orders SET status = CASE WHEN status = 'completed' THEN 'completed' ELSE 'in_progress' END")
    op.drop_index("ix_clients_code", table_name="clients")
    op.drop_column("clients", "code")
