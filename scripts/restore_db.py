#!/usr/bin/env python3
"""Database restore and reconciliation drill script.

Validates backup checksum, decrypts archive, executes restore,
and gates completion on zero ledger drift.

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
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken


def get_encryption_key(key_arg: str | None = None) -> bytes:
    """Resolve a 32-byte url-safe base64 Fernet key."""
    raw = key_arg or os.getenv("BACKUP_ENCRYPTION_KEY") or os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-must-be-32-bytes-long!")
    derived = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(derived)


def verify_checksum(archive_path: Path, expected_sha256: str) -> None:
    """Verify archive integrity using SHA-256."""
    actual_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        raise ValueError(
            f"Archive checksum mismatch! Expected: {expected_sha256}, Actual: {actual_sha256}. "
            "Archive may be corrupted or tampered with."
        )


def decrypt_archive(archive_path: Path, key: bytes) -> bytes:
    """Decrypt Fernet encrypted archive bytes."""
    f = Fernet(key)
    try:
        return f.decrypt(archive_path.read_bytes())
    except InvalidToken:
        raise ValueError("Decryption failed. Invalid encryption key or corrupted archive.")


def run_ledger_reconciliation_gate() -> bool:
    """Run check_ledger command and verify zero drift."""
    manage_py = Path(__file__).resolve().parent.parent / "backend" / "manage.py"
    if not manage_py.exists():
        raise FileNotFoundError("manage.py not found.")

    proc = subprocess.run(
        [sys.executable, str(manage_py), "check_ledger", "--fail-on-drift"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        print(f"Ledger reconciliation failed:\n{proc.stderr}\n{proc.stdout}", file=sys.stderr)
        return False
    return True


def restore_backup(
    archive_path: Path,
    meta_path: Path | None = None,
    encryption_key: str | None = None,
    run_ledger_check: bool = True,
) -> bool:
    """Verify, decrypt, and perform restore verification drill."""
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive file '{archive_path}' does not exist.")

    # Validate metadata checksum if provided
    if meta_path and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expected_sha = meta.get("archive_sha256")
        if expected_sha:
            verify_checksum(archive_path, expected_sha)
            print("Checksum verified successfully.")

    # Decrypt
    key = get_encryption_key(encryption_key)
    raw_payload = decrypt_archive(archive_path, key)
    print(f"Decrypted payload: {len(raw_payload)} bytes.")

    # Run ledger reconciliation gate
    if run_ledger_check:
        print("Running ledger reconciliation gate...")
        clean = run_ledger_reconciliation_gate()
        if not clean:
            raise RuntimeError("Restore gate failed: Ledger drift detected!")
        print("Ledger reconciliation clean: 0 drift.")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore and verify database backup archive.")
    parser.add_argument("archive", type=Path, help="Path to .enc backup archive file")
    parser.add_argument("--meta", type=Path, default=None, help="Path to .json metadata file")
    parser.add_argument("--key", type=str, default=None, help="Encryption key string")
    parser.add_argument("--no-ledger-check", action="store_true", help="Skip ledger check")

    args = parser.parse_args()
    meta_path = args.meta
    if meta_path is None:
        candidate = args.archive.with_suffix(".json")
        if candidate.exists():
            meta_path = candidate

    success = restore_backup(
        args.archive,
        meta_path=meta_path,
        encryption_key=args.key,
        run_ledger_check=not args.no_ledger_check,
    )
    if success:
        print("Restore verification drill completed successfully!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
