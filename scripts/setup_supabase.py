from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from easy_social import create_app
from easy_social.extensions import db
from easy_social.schema import ensure_poll_schema


def main() -> None:
    app = create_app()
    with app.app_context():
        ensure_poll_schema()

        if app.config.get("MEDIA_STORAGE_BACKEND") != "supabase":
            print("Initialized database. Set MEDIA_STORAGE_BACKEND=supabase to create a bucket.")
            return

        try:
            from supabase import create_client
        except ImportError as exc:
            raise SystemExit("Install supabase before running this script.") from exc

        url = app.config.get("SUPABASE_URL")
        key = app.config.get("SUPABASE_SERVICE_ROLE_KEY")
        bucket = app.config["SUPABASE_STORAGE_BUCKET"]
        if not url or not key:
            raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

        client = create_client(url, key)
        existing = {
            getattr(item, "name", item.get("name") if isinstance(item, dict) else None)
            for item in client.storage.list_buckets()
        }
        if bucket not in existing:
            client.storage.create_bucket(bucket, options={"public": True})
        else:
            client.storage.update_bucket(bucket, options={"public": True})

        print(f"Initialized database and Supabase Storage bucket: {bucket}")


if __name__ == "__main__":
    env_file = Path(".env") if Path(".env").exists() else Path("env")
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
    os.environ.setdefault("MEDIA_STORAGE_BACKEND", "supabase")
    main()
