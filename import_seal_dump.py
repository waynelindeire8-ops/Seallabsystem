#!/usr/bin/env python3
"""Add the new phpMyAdmin dump of the legacy `seal` MySQL DB into seal_mw.db (additive, idempotent).

Usage: python3 import_seal_dump.py <dump.sql> <seal_mw.db>
"""
import sys, re, shutil, sqlite3, collections
from datetime import datetime, timezone

def parse_values(s, i):
    rows = []
    while True:
        while s[i] in ' \n\r\t,': i += 1
        if s[i] == ';': return rows, i + 1
        assert s[i] == '(', s[i:i+60]
        i += 1; row = []
        while True:
            while s[i] in ' \t\n\r': i += 1
            if s[i] == "'":
                i += 1; buf = []
                while True:
                    c = s[i]
                    if c == '\\':
                        nx = s[i+1]
                        buf.append({'n':'\n','r':'\r','t':'\t','0':'\0','Z':'\x1a','b':'\b'}.get(nx, nx)); i += 2
                    elif c == "'":
                        if s[i+1] == "'": buf.append("'"); i += 2
                        else: i += 1; break
                    else: buf.append(c); i += 1
                row.append(''.join(buf))
            else:
                j = i
                while s[j] not in ',)': j += 1
                tok = s[i:j].strip(); i = j
                row.append(None if tok.upper() == 'NULL' else tok)
            while s[i] in ' \t\n\r': i += 1
            if s[i] == ',': i += 1; continue
            if s[i] == ')': i += 1; break
        rows.append(row)

def load_dump(path):
    s = open(path, encoding='latin-1').read()
    tables, cols = {}, {}
    for m in re.finditer(r"INSERT INTO `(\w+)` \(([^)]*)\) VALUES\s*", s):
        t = m.group(1); cols[t] = [x.strip(' `') for x in m.group(2).split(',')]
        rows, _ = parse_values(s, m.end())
        tables.setdefault(t, []).extend(rows)
    return tables, cols

PK = {'bills':'bill_id','category':'category_id','clients':'client_id','clinics':'clinic_id','group':'group_id',
      'options':'optionn_id','ref_range':'ref_range_id','requested_tests':'rqtest_id','specimen':'specimen_id',
      'tests':'test_id','test_parameters':'test_parameter_id','test_results':'test_result_id','units':'units_id',
      'users':'user_id','products':'product_id','suppliers':'supplier_id','product_clients':'pclient_id',
      'product_sales':'psale_id','misc':'misc_id','usertype':'usertype_id','payment_mode':'payment_mode_id'}

S = lambda x: (x or '').strip()

def main(dump, db):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = db.replace('.db', f'.before_seal_dump_import_{stamp}.db')
    shutil.copy2(db, backup)
    print('backup:', backup)
    tables, cols = load_dump(dump)
    conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=OFF')
    report = collections.OrderedDict()
    try:
        conn.execute('BEGIN')
        # 1) raw archive mirrors: add rows whose primary key is new
        for tb, pk in PK.items():
            if tb not in tables: continue
            cn = cols[tb]; ki = cn.index(pk)
            have = {r[0] for r in conn.execute(f'SELECT "{pk}" FROM "legacy_{tb}"')}
            new = [r for r in tables[tb] if r[ki] not in have]
            if new:
                q = f'INSERT INTO "legacy_{tb}" ({",".join(chr(34)+c+chr(34) for c in cn)}) VALUES ({",".join("?"*len(cn))})'
                conn.executemany(q, new)
            report[f'legacy_{tb} +'] = len(new)

        # 2) clients: dedupe on trimmed (name, phone, email), same as the earlier import
        lc_rows = [dict(zip(cols['clients'], r)) for r in tables['clients']]
        lc_rows.sort(key=lambda r: int(r['client_id']))
        live = {}
        for r in conn.execute('SELECT id,name,phone,email FROM clients ORDER BY id'):
            live.setdefault((S(r['name']), S(r['phone']), S(r['email'])), r['id'])
        cmap, added_clients = {}, 0
        for r in lc_rows:
            key = (S(r['name']), S(r['phone']), S(r['email']))
            if key not in live:
                cur = conn.execute('INSERT INTO clients (name, contact_person, phone, email, address, active) VALUES (?,?,?,?,?,?)',
                                   (S(r['name']), None, r['phone'], r['email'], None, 0 if r['deleted'] == '1' else 1))
                live[key] = cur.lastrowid; added_clients += 1
            cmap[r['client_id']] = live[key]
        report['clients +'] = added_clients
        cname = {r['id']: r['name'] for r in conn.execute('SELECT id,name FROM clients')}

        # 3) legacy test id -> test_catalog id (trimmed, case-insensitive name)
        cat = {}
        for r in conn.execute('SELECT id,name FROM test_catalog ORDER BY id'):
            cat.setdefault(S(r['name']).casefold(), r['id'])
        tmap = {}
        for r in tables['tests']:
            d = dict(zip(cols['tests'], r)); k = S(d['test_name']).casefold()
            if k in cat: tmap[d['test_id']] = cat[k]

        # 4) results index (live client, test) -> rows ordered by id
        res = collections.defaultdict(list)
        trs = [dict(zip(cols['test_results'], r)) for r in tables['test_results']]
        trs.sort(key=lambda r: int(r['test_result_id']))
        for r in trs:
            if r['client_id'] in cmap: res[(cmap[r['client_id']], r['test_id'])].append(r)

        # 5) samples + sample_tests for requests not yet imported
        have_codes = {r[0] for r in conn.execute("SELECT sample_code FROM samples")}
        rqs = [dict(zip(cols['requested_tests'], r)) for r in tables['requested_tests']]
        rqs.sort(key=lambda r: int(r['rqtest_id']))
        n_s = 0; skipped = collections.Counter(); with_result = 0
        for r in rqs:
            code = 'LEGACY-RQ-' + r['rqtest_id']
            if code in have_codes: continue
            if r['client_id'] not in cmap: skipped['client not in clients table'] += 1; continue
            if r['test_id'] not in tmap: skipped['test not in tests table'] += 1; continue
            cid = cmap[r['client_id']]; done = r['done'] == '1'
            created = r['request_date'] or r['visit_date'] or None
            notes = f"Legacy request; doctor: {S(r['doctor_name'])}" if S(r['doctor_name']) else 'Imported legacy request'
            cur = conn.execute("""INSERT INTO samples (sample_code, client_id, sample_type_id, patient_name, priority, status, created_at, notes)
                                  VALUES (?,?,?,?,?,?,?,?)""",
                               (code, cid, 1, cname[cid], 'routine', 'reported' if done else 'registered', created, notes))
            sid = cur.lastrowid
            cands = res.get((cid, r['test_id']), [])
            pick = None
            if cands:
                same_visit = [x for x in cands if x['v_date'] and x['v_date'] == r['visit_date']]
                pick = (same_visit or cands)[-1]
            result = unit = rng = note = upd = None
            if pick:
                result, unit, rng, note = pick['test_result'], pick['units'], pick['ref_range'], pick['comment']
                upd = int(pick['report_date']) if (pick['report_date'] or '').isdigit() else None
                with_result += 1
            conn.execute("""INSERT INTO sample_tests (sample_id, test_catalog_id, status, result, unit, reference_range, flagged, notes, updated_at)
                            VALUES (?,?,?,?,?,?,0,?,?)""",
                         (sid, tmap[r['test_id']], 'completed' if done else 'pending', result, unit, rng, note, upd))
            n_s += 1
        report['samples + (and sample_tests +)'] = n_s
        report['  of which with a result attached'] = with_result
        for k, v in skipped.items(): report[f'  skipped: {k}'] = v
        conn.commit()
    except Exception:
        conn.rollback(); raise
    print('\n'.join(f'{k:45} {v}' for k, v in report.items()))
    for t in ('clients', 'samples', 'sample_tests'):
        print(f'{t:15} total now', conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
    print('integrity:', conn.execute('PRAGMA integrity_check').fetchone()[0],
          '| fk violations:', len(conn.execute('PRAGMA foreign_key_check').fetchall()))
    conn.close()

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
