"""Initial migration — create all 5 core tables.

Revision ID: 0001
Revises:
Create Date: 2026-06-11

Tables:
  - users
  - projects
  - model_files (with source_format enum)
  - conversion_jobs (with job_status enum)
  - share_links
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    source_format_enum = sa.Enum("ifc", "dae", "obj", "glb", name="source_format_enum")
    source_format_enum.create(op.get_bind(), checkfirst=True)

    job_status_enum = sa.Enum("pending", "running", "ready", "failed", name="job_status_enum")
    job_status_enum.create(op.get_bind(), checkfirst=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- model_files ---
    op.create_table(
        "model_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("uploader_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("source_format", source_format_enum, nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_storage_key", sa.String(512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
    )

    # --- conversion_jobs ---
    op.create_table(
        "conversion_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_file_id",
            UUID(as_uuid=True),
            sa.ForeignKey("model_files.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("status", job_status_enum, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("glb_storage_key", sa.String(512), nullable=True),
        sa.Column("thumbnail_storage_key", sa.String(512), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )

    # --- share_links ---
    op.create_table(
        "share_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("model_file_id", UUID(as_uuid=True), sa.ForeignKey("model_files.id"), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("share_links")
    op.drop_table("conversion_jobs")
    op.drop_table("model_files")
    op.drop_table("projects")
    op.drop_table("users")

    sa.Enum(name="job_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="source_format_enum").drop(op.get_bind(), checkfirst=True)
