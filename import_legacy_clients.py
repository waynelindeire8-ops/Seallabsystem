from __future__ import annotations

import csv
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
DB_PATH = PROJECT / "seal_mw.db"
SOURCE_PATH = Path("/home/ubuntu/seal_import_staging/product_clients.tsv")
BACKUP_PATH = PROJECT / f"seal_mw.db.before_seal_import_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

if not SOURCE_PATH.exists():
    raise SystemExit(f"Missing staged source file: {SOURCE_PATH}")

shutil.copy2(DB_PATH, BACKUP_PATH)

with SOURCE_PATH.open("r", encoding="utf-8", newline="") as source:
    rows = list(csv.DictReader(source, delimiter="\t"))

inserted = 0
updated = 0
skipped = 0

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
try:
    conn.execute("BEGIN")
    for row in rows:
        name = (row.get("client_name") or "").strip()
        address = (row.get("address") or "").strip()
        email = (row.get("email") or "").strip()
        phone = (row.get("phone") or "").strip()
        active = 0 if str(row.get("deleted", "0")).strip() == "1" else 1
        if not name:
            skipped += 1
            continue

        existing = conn.execute(
            """SELECT id FROM clients
               WHERE name = ? AND COALESCE(address, '') = ?
                 AND COALESCE(email, '') = ? AND COALESCE(phone, '') = ?
               LIMIT 1""",
            (name, address, email, phone),
        ).fetchone()

        if existing:
            conn.execute("UPDATE clients SET active = ? WHERE id = ?", (active, existing["id"]))
            updated += 1
        else:
            conn.execute(
                """INSERT INTO clients (name, contact_person, phone, email, address, active)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, None, phone, email, address, active),
            )
            inserted += 1

    conn.commit()
except Exception:
    conn.rollback()
    conn.close()
    raise
else:
    conn.close()

print(f"source_rows={len(rows)} inserted={inserted} updated={updated} skipped={skipped}")
print(f"backup={BACKUP_PATH}")
