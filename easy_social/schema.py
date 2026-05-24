from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db


def ensure_poll_schema() -> None:
    """Bring older databases in line with poll-post models (idempotent)."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "post" in table_names:
        column_names = {column["name"] for column in inspector.get_columns("post")}
        if "post_type" not in column_names:
            dialect = db.engine.dialect.name
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE post "
                        "ADD COLUMN IF NOT EXISTS post_type VARCHAR(20) "
                        "NOT NULL DEFAULT 'standard'"
                    )
                )
                db.session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_post_post_type ON post (post_type)"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "ALTER TABLE post "
                        "ADD COLUMN post_type VARCHAR(20) NOT NULL DEFAULT 'standard'"
                    )
                )
                db.session.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_post_post_type ON post (post_type)")
                )
            db.session.commit()

    db.create_all()
