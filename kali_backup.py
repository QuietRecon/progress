#!/usr/bin/env python3
"""
kali_backup.py

Create a restorable Linux system backup archive using GNU tar.

What it does:
- Archives the root filesystem /
- Preserves permissions, ownership, symlinks, device files
- Stores ACLs and xattrs when supported by tar
- Excludes virtual/runtime filesystems and temporary mountpoints
- Writes a compressed .tar.gz archive to a destination directory

Run as root:
    sudo python3 kali_backup.py backup /path/to/backup-dir

Example:
    sudo python3 kali_backup.py backup /mnt/usb/backups

Restore is intentionally NOT automated here because restore should be done
from a live USB/rescue environment after you've mounted the target root.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDES = [
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/tmp",
    "/mnt",
    "/media",
    "/lost+found",
    "/swapfile",
]


def require_root() -> None:
    if os.geteuid() != 0:
        print("This script must be run as root.", file=sys.stderr)
        sys.exit(1)


def require_tar() -> None:
    if shutil.which("tar") is None:
        print("GNU tar is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)


def build_backup_path(dest_dir: Path) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    hostname = os.uname().nodename
    return dest_dir / f"{hostname}-kali-backup-{timestamp}.tar.gz"


def run_backup(dest_dir: Path) -> None:
    require_root()
    require_tar()

    dest_dir.mkdir(parents=True, exist_ok=True)
    archive_path = build_backup_path(dest_dir)

    # If the destination is inside the filesystem being backed up, exclude it.
    dynamic_excludes = list(EXCLUDES)
    try:
        resolved_dest = dest_dir.resolve()
        if str(resolved_dest).startswith("/"):
            dynamic_excludes.append(str(resolved_dest))
    except Exception:
        pass

    cmd = [
        "tar",
        "--create",
        "--gzip",
        "--file",
        str(archive_path),
        "--one-file-system",
        "--acls",
        "--xattrs",
        "--numeric-owner",
        "--preserve-permissions",
    ]

    for path in dynamic_excludes:
        cmd.extend(["--exclude", path.lstrip("/")])

    # Change directory to / so archive paths are relative, not absolute.
    cmd.extend(["-C", "/", "."])

    print("Creating backup archive:")
    print(f"  {archive_path}")
    print("\nCommand:")
    print(" ", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"\nBackup failed with exit code {exc.returncode}.", file=sys.stderr)
        sys.exit(exc.returncode)

    print("\nBackup complete.")
    print(f"Archive created: {archive_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up a Kali/Linux system to tar.gz")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a backup archive")
    backup_parser.add_argument(
        "destination",
        type=Path,
        help="Directory where the backup archive will be written",
    )

    args = parser.parse_args()

    if args.command == "backup":
        run_backup(args.destination)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
