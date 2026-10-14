#!/usr/bin/env python3
"""Fill test prices (MK) from a CSV. Usage: python3 apply_prices.py unpriced_tests.csv seal_mw.db
CSV needs columns: id, price_mwk (rows with an empty price_mwk are ignored). Backs up the DB first."""
import csv, shutil, sqlite3, sys
from datetime import datetime
csv_path, db = sys.argv[1], sys.argv[2]
shutil.copy2(db, db.replace('.db', f'.before_prices_{datetime.now():%Y%m%d%H%M%S}.db'))
c = sqlite3.connect(db); n = 0
for r in csv.DictReader(open(csv_path, newline='', encoding='utf-8-sig')):
    p = (r.get('price_mwk') or '').replace(',', '').replace('MK', '').strip()
    if not p: continue
    n += c.execute('UPDATE test_catalog SET price=? WHERE id=?', (float(p), int(r['id']))).rowcount
c.commit(); print('prices updated:', n)
