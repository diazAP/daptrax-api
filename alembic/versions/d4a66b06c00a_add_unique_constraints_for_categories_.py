from alembic import op


# revision identifiers, used by Alembic.
revision = "d4a66b06c00a"
down_revision = "5adc2849c09c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_categories_user_name",
        "categories",
        ["user_id", "name"],
    )
    op.create_unique_constraint(
        "uq_accounts_user_name",
        "accounts",
        ["user_id", "name"],
    )

    op.create_index(
        "idx_transactions_user_date",
        "transactions",
        ["user_id", "transaction_date"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_user_type_date",
        "transactions",
        ["user_id", "transaction_type", "transaction_date"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_user_category",
        "transactions",
        ["user_id", "category_id"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_user_account",
        "transactions",
        ["user_id", "account_id"],
        unique=False,
    )

    op.create_index(
        "idx_categories_user_id",
        "categories",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_accounts_user_id",
        "accounts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_audit_logs_actor_user_id",
        "audit_logs",
        ["actor_user_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_user_settings_user_id",
        "user_settings",
        ["user_id"],
    )
    op.create_unique_constraint(
        "uq_user_google_accounts_user_id",
        "user_google_accounts",
        ["user_id"],
    )
    op.create_unique_constraint(
        "uq_user_google_accounts_google_sub",
        "user_google_accounts",
        ["google_sub"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_google_accounts_google_sub",
        "user_google_accounts",
        type_="unique",
    )
    op.drop_constraint(
        "uq_user_google_accounts_user_id",
        "user_google_accounts",
        type_="unique",
    )
    op.drop_constraint(
        "uq_user_settings_user_id",
        "user_settings",
        type_="unique",
    )

    op.drop_index("idx_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("idx_accounts_user_id", table_name="accounts")
    op.drop_index("idx_categories_user_id", table_name="categories")
    op.drop_index("idx_transactions_user_account", table_name="transactions")
    op.drop_index("idx_transactions_user_category", table_name="transactions")
    op.drop_index("idx_transactions_user_type_date", table_name="transactions")
    op.drop_index("idx_transactions_user_date", table_name="transactions")

    op.drop_constraint(
        "uq_accounts_user_name",
        "accounts",
        type_="unique",
    )
    op.drop_constraint(
        "uq_categories_user_name",
        "categories",
        type_="unique",
    )