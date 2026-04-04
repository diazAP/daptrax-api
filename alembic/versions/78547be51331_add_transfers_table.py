from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '78547be51331'
down_revision = 'd4a66b06c00a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("from_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_transfers_user_date",
        "transfers",
        ["user_id", "transfer_date"],
        unique=False,
    )
    op.create_index(
        "idx_transfers_user_from_account",
        "transfers",
        ["user_id", "from_account_id"],
        unique=False,
    )
    op.create_index(
        "idx_transfers_user_to_account",
        "transfers",
        ["user_id", "to_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_transfers_user_to_account", table_name="transfers")
    op.drop_index("idx_transfers_user_from_account", table_name="transfers")
    op.drop_index("idx_transfers_user_date", table_name="transfers")
    op.drop_table("transfers")
