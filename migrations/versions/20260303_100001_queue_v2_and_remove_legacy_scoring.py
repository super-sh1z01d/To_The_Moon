"""queue v2 pipeline tables + legacy scoring cleanup

Revision ID: 20260303_queue_v2
Revises: add_role_to_users
Create Date: 2026-03-03

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260303_queue_v2"
down_revision = "add_role_to_users"
branch_labels = None
depends_on = None


LEGACY_SETTING_KEYS = (
    "weight_s",
    "weight_l",
    "weight_m",
    "weight_t",
    "score_smoothing_alpha",
    "max_price_change_5m",
)


def _ensure_index(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name in existing:
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("processing_jobs"):
        op.create_table(
            "processing_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("job_type", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column(
                "run_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("idempotency_key", sa.Text(), nullable=True),
            sa.Column("token_id", sa.Integer(), sa.ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True),
            sa.Column("leased_by", sa.String(length=120), nullable=True),
            sa.Column(
                "payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.CheckConstraint(
                "status in ('queued','leased','retry','done','deadletter','cancelled')",
                name="ck_processing_jobs_status",
            ),
        )

    _ensure_index("idx_processing_jobs_status", "processing_jobs", ["status"])
    _ensure_index("idx_processing_jobs_type", "processing_jobs", ["job_type"])
    _ensure_index("idx_processing_jobs_priority", "processing_jobs", ["priority"])
    _ensure_index("idx_processing_jobs_run_at", "processing_jobs", ["run_at"])
    _ensure_index("idx_processing_jobs_lease_until", "processing_jobs", ["lease_until"])
    _ensure_index("idx_processing_jobs_token_id", "processing_jobs", ["token_id"])
    _ensure_index("idx_processing_jobs_idempotency_key", "processing_jobs", ["idempotency_key"])
    _ensure_index("idx_processing_jobs_leased_by", "processing_jobs", ["leased_by"])

    inspector = sa.inspect(bind)
    if not inspector.has_table("token_runtime_state"):
        op.create_table(
            "token_runtime_state",
            sa.Column("token_id", sa.Integer(), sa.ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_activation_check_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("score_band", sa.String(length=20), nullable=True),
            sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
        )

    _ensure_index("idx_token_runtime_state_last_scored_at", "token_runtime_state", ["last_scored_at"])
    _ensure_index("idx_token_runtime_state_last_activation", "token_runtime_state", ["last_activation_check_at"])
    _ensure_index("idx_token_runtime_state_score_band", "token_runtime_state", ["score_band"])
    _ensure_index("idx_token_runtime_state_backoff", "token_runtime_state", ["backoff_until"])

    # Hard cleanup of legacy settings keys.
    for key in LEGACY_SETTING_KEYS:
        op.execute(sa.text("DELETE FROM app_settings WHERE key = :key").bindparams(key=key))

    # Enforce hybrid-only active model.
    op.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES ('scoring_model_active', 'hybrid_momentum')
        ON CONFLICT (key) DO UPDATE
        SET value = 'hybrid_momentum'
        """
    )

    # latest_token_scores should not expose legacy model in current state table.
    inspector = sa.inspect(bind)
    if inspector.has_table("latest_token_scores"):
        op.execute(
            """
            UPDATE latest_token_scores
            SET scoring_model = 'hybrid_momentum'
            WHERE scoring_model IS NULL OR scoring_model <> 'hybrid_momentum'
            """
        )

    # Cleanup deprecated on-chain pool metadata path.
    inspector = sa.inspect(bind)
    if inspector.has_table("pool_metadata"):
        _drop_index_if_exists("ix_pool_metadata_fetched_at", "pool_metadata")
        _drop_index_if_exists("ix_pool_metadata_pool_type", "pool_metadata")
        _drop_index_if_exists("ix_pool_metadata_owner_program", "pool_metadata")
        _drop_index_if_exists("idx_pool_metadata_owner", "pool_metadata")
        _drop_index_if_exists("idx_pool_metadata_type", "pool_metadata")
        op.drop_table("pool_metadata")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("token_runtime_state"):
        _drop_index_if_exists("idx_token_runtime_state_backoff", "token_runtime_state")
        _drop_index_if_exists("idx_token_runtime_state_score_band", "token_runtime_state")
        _drop_index_if_exists("idx_token_runtime_state_last_activation", "token_runtime_state")
        _drop_index_if_exists("idx_token_runtime_state_last_scored_at", "token_runtime_state")
        op.drop_table("token_runtime_state")

    inspector = sa.inspect(bind)
    if inspector.has_table("processing_jobs"):
        _drop_index_if_exists("idx_processing_jobs_leased_by", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_idempotency_key", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_token_id", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_lease_until", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_run_at", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_priority", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_type", "processing_jobs")
        _drop_index_if_exists("idx_processing_jobs_status", "processing_jobs")
        op.drop_table("processing_jobs")
