"""Find the Supabase transaction pooler region for the project in .env."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv

REGIONS = [
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-south-1",
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ca-central-1",
    "sa-east-1",
]


def pooler_url(region: str, project_ref: str, password: str, port: int) -> str:
    user = f"postgres.{project_ref}"
    host = f"aws-0-{region}.pooler.supabase.com"
    return f"postgresql://{user}:{password}@{host}:{port}/postgres"


def main() -> None:
    load_dotenv(Path(".env"))
    direct = os.environ["DATABASE_URL"]
    parsed = urlsplit(direct)
    password = parsed.password or ""
    project_ref = ""
    if parsed.hostname and parsed.hostname.startswith("db."):
        project_ref = parsed.hostname.removeprefix("db.").split(".")[0]

    supabase_url = os.environ.get("SUPABASE_URL", "")
    if not project_ref and supabase_url:
        project_ref = urlsplit(supabase_url).hostname.split(".")[0]

    print(f"Project ref: {project_ref}")

    for prefix in ("aws-0", "aws-1"):
        for region in REGIONS:
            for port in (6543, 5432):
                host = f"{prefix}-{region}.pooler.supabase.com"
                url = f"postgresql://postgres.{project_ref}:{password}@{host}:{port}/postgres"
                try:
                    with psycopg.connect(url, connect_timeout=8) as conn:
                        with conn.cursor() as cur:
                            cur.execute("select 1")
                            cur.fetchone()
                    print(f"OK  {host}:{port}")
                    print(url.replace(password, "***"))
                    return
                except Exception as exc:
                    print(f"FAIL {host}:{port} {exc!r}")

    for region in REGIONS:
        for port in (6543, 5432):
            url = pooler_url(region, project_ref, password, port)
            try:
                with psycopg.connect(url, connect_timeout=8) as conn:
                    with conn.cursor() as cur:
                        cur.execute("select 1")
                        cur.fetchone()
                print(f"OK  {region}:{port}")
                print(url.replace(password, "***"))
                return
            except Exception as exc:
                print(f"FAIL {region}:{port} {type(exc).__name__}: {exc!r}")


if __name__ == "__main__":
    main()
