#!/usr/bin/env python3
"""Automated database backup script with client-side encryption and SHA-256 checksumming.

See docs/architecture/SECURITY.md Section 10 and docs/ROADMAP.md Milestone 6.3.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet


def get_encryption_key(key_arg: str | None = None) -> bytes:
    """Resolve a 32-byte url-safe base64 Fernet key."""
    raw = key_arg or os.getenv("BACKUP_ENCRYPTION_KEY") or os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-must-be-32-bytes-long!")
    # Derive a deterministic Fernet key using SHA-256
    derived = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(derived)


def perform_dump(database_url: str) -> bytes:
    """Execute pg_dump or fallback to django dumpdata to produce SQL/JSON bytes."""
    parsed = urlparse(database_url)
    
    # Try pg_dump first if command exists
    try:
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 5432)
        user = parsed.username or "postgres"
        dbname = parsed.path.lstrip("/") or "xaku"

        cmd = [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "--no-owner",
            "--no-privileges",
            "-Fc",  # custom pg_dump format
            dbname,
        ]
        proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0 and len(proc.stdout) > 0:
            return proc.stdout
    except Exception:
        pass

    # Fallback to python manage.py dumpdata
    manage_py = Path(__file__).resolve().parent.parent / "backend" / "manage.py"
    if manage_py.exists():
        proc = subprocess.run(
            [sys.executable, str(manage_py), "dumpdata", "--natural-foreign", "--natural-primary", "-e", "contenttypes", "-e", "auth.Permission"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode == 0:
            return proc.stdout

    raise RuntimeError("Failed to generate database dump via pg_dump or dumpdata.")


def run_backup(
    output_dir: Path,
    database_url: str | None = None,
    encryption_key: str | None = None,
) -> tuple[Path, Path]:
    """Generate encrypted backup and metadata file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    db_url = database_url or os.getenv("DATABASE_URL", "postgres://xaku:xaku_dev_password@127.0.0.1:5432/xaku")
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_id = str(uuid.uuid4())

    raw_dump = perform_dump(db_url)
    raw_sha256 = hashlib.sha256(raw_dump).hexdigest()

    # Encrypt
    fernet_key = get_encryption_key(encryption_key)
    f = Fernet(fernet_key)
    encrypted_bytes = f.encrypt(raw_dump)
    enc_sha256 = hashlib.sha256(encrypted_bytes).hexdigest()

    # Write encrypted archive
    archive_file = output_dir / f"backup_{timestamp}_{backup_id[:8]}.enc"
    archive_file.write_bytes(encrypted_bytes)

    # Write metadata
    meta = {
        "backup_id": backup_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "encrypted": True,
        "algorithm": "Fernet/AES-128-CBC",
        "archive_filename": archive_file.name,
        "archive_size_bytes": len(encrypted_bytes),
        "archive_sha256": enc_sha256,
        "raw_sha256": raw_sha256,
        "version": "1.0.0",
    }
    meta_file = output_dir / f"backup_{timestamp}_{backup_id[:8]}.json"
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return archive_file, meta_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Create encrypted database backup with checksum verification.")
    parser.add_argument("--output-dir", type=Path, default=Path("backups"), help="Directory to save backup files")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    parser.add_argument("--key", type=str, default=None, help="Encryption key string")

    args = parser.parse_args()
    archive, meta = run_backup(args.output_dir, args.db_url, args.key)
    print(f"Backup created successfully:")
    print(f"  Archive:  {archive}")
    print(f"  Metadata: {meta}")


if __name__ == "__main__":
    main()
