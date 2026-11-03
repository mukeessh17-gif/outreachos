"""Create or restore a PostgreSQL custom-format backup without printing credentials."""

import argparse
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def _postgres_environment() -> tuple[list[str], dict[str, str]]:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured in .env.")
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("Backup and restore require a PostgreSQL DATABASE_URL.")
    command = [
        "--host", url.host or "localhost",
        "--port", str(url.port or 5432),
        "--username", url.username or "",
        "--dbname", url.database or "",
        "--no-password",
    ]
    environment = os.environ.copy()
    if url.password is not None:
        environment["PGPASSWORD"] = url.password
    return command, environment


def backup(destination: Path) -> None:
    command, environment = _postgres_environment()
    target = destination.resolve()
    if target.exists():
        raise FileExistsError("Backup destination already exists; choose a new path.")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["pg_dump", *command, "--format=custom", "--file", str(target)],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("pg_dump was not found. Install the free PostgreSQL command-line tools.") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError("pg_dump failed; verify database connectivity and PostgreSQL tool versions.") from error
    print(f"Backup created at {target}")


def restore(source: Path, confirmed: bool) -> None:
    if not confirmed:
        raise RuntimeError("Restore is destructive. Rerun with --confirm after verifying the target database.")
    backup_path = source.resolve()
    if not backup_path.is_file():
        raise FileNotFoundError("Backup file was not found.")
    command, environment = _postgres_environment()
    try:
        subprocess.run(
            [
                "pg_restore",
                *command,
                "--clean",
                "--if-exists",
                "--no-owner",
                str(backup_path),
            ],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("pg_restore was not found. Install the free PostgreSQL command-line tools.") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError("pg_restore failed; verify database access and the backup file.") from error
    print("Restore completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("destination", type=Path)
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("source", type=Path)
    restore_parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.action == "backup":
        backup(args.destination)
    else:
        restore(args.source, args.confirm)


if __name__ == "__main__":
    main()
