from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt
from datetime import datetime

samples_bp = Blueprint('samples', __name__, url_prefix='/samples')

WORKFLOW = ['registered', 'triaged', 'analysis', 'review', 'approved', 'reported']
WORKFLOW_INDEX = {s: i for i, s in enumerate(WORKFLOW)}

STAGE_ROLES = {
    'triaged': ['admin', 'lab_manager', 'lab_tech', 'sample_collector'],
    'analysis': ['admin', 'lab_manager', 'lab_tech'],
    'review': ['admin', 'lab_manager'],
    'approved': ['admin', 'lab_manager'],
    'reported': ['admin', 'lab_manager', 'lab_tech'],
}


def _generate_sample_code(conn):
    today = datetime.now().strftime('%Y%m%d')
    row = conn.execute(
        "SELECT COUNT(*) c FROM samples WHERE sample_code LIKE ?",
        (f'SMW-{today}-%',)
    ).fetchone()
    seq = row['c'] + 1
    return f'SMW-{today}-{seq:04d}'


@samples_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('samples/list.html')

@samples_bp.route('/<int:sample_id>')
@login_required
def detail_page(sample_id):
    return render_template('samples/detail.html')

@samples_bp.route('/register', strict_slashes=False)
@login_required
def register_page():
    return render_template('samples/register.html')

@samples_bp.route('/<int:sample_id>/report')
@login_required
def report_page(sample_id):
    return render_template('samples/report.html')


@samples_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    sample_type = request.args.get('type', '')
    search = request.args.get('search', '')

    query = """SELECT s.*, st.name as type_name, c.name as client_name
               FROM samples s
               LEFT JOIN sample_types st ON s.sample_type_id = st.id
               LEFT JOIN clients c ON s.client_id = c.id
               WHERE 1=1"""
    params = []

    if status:
        query += " AND s.status = ?"
        params.append(status)
    if priority:
        query += " AND s.priority = ?"
        params.append(priority)
    if sample_type:
        query += " AND s.sample_type_id = ?"
        params.append(sample_type)
    if search:
        query += " AND (s.sample_code LIKE ? OR s.patient_name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    query += " ORDER BY s.created_at DESC"
    rows = db.execute(query, params).fetchall()
    
    return jsonify([dict(r) for r in rows])


@samples_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()

    sample_code = _generate_sample_code(db)

    cursor = db.execute(
        """INSERT INTO samples (sample_code, client_id, sample_type_id, patient_name, patient_dob,
           patient_gender, priority, status, registered_by, notes, estimated_turnaround)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'registered', ?, ?, ?)""",
        (
            sample_code,
            data.get('client_id') or None,
            data['sample_type_id'],
            data['patient_name'],
            data.get('patient_dob'),
            data.get('patient_gender', ''),
            data.get('priority', 'routine'),
            claims['id'],
            data.get('notes'),
            data.get('estimated_turnaround')
        )
    )
    sample_id = cursor.lastrowid

    db.execute(
        "INSERT INTO sample_status_log (sample_id, from_status, to_status, user_id, username, notes) VALUES (?, NULL, 'registered', ?, ?, 'Sample registered')",
        (sample_id, claims['id'], claims['username'])
    )

    if data.get('test_ids'):
        for tid in data['test_ids']:
            db.execute(
                "INSERT INTO sample_tests (sample_id, test_catalog_id, status) VALUES (?, ?, 'pending')",
                (sample_id, tid)
            )

    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'sample', sample_id, f'Created sample {sample_code}', request.remote_addr)
    
    return jsonify({'id': sample_id, 'sample_code': sample_code}), 201


@samples_bp.route('/api/<int:sample_id>', methods=['GET'])
@login_required
def api_get(sample_id):
    db = get_db()
    sample = db.execute(
        """SELECT s.*, st.name as type_name, c.name as client_name
           FROM samples s
           LEFT JOIN sample_types st ON s.sample_type_id = st.id
           LEFT JOIN clients c ON s.client_id = c.id
           WHERE s.id = ?""",
        (sample_id,)
    ).fetchone()

    if not sample:
        
        return jsonify({'error': 'Sample not found'}), 404

    tests = db.execute(
        """SELECT st.*, tc.name as test_name, tc.unit as test_unit, tc.reference_text
           FROM sample_tests st
           JOIN test_catalog tc ON st.test_catalog_id = tc.id
           WHERE st.sample_id = ?""",
        (sample_id,)
    ).fetchall()

    log = db.execute(
        """SELECT l.*, u.first_name, u.last_name
           FROM sample_status_log l
           LEFT JOIN users u ON l.user_id = u.id
           WHERE l.sample_id = ?
           ORDER BY l.created_at ASC""",
        (sample_id,)
    ).fetchall()

    
    return jsonify({
        'sample': dict(sample),
        'tests': [dict(t) for t in tests],
        'log': [dict(l) for l in log]
    })


@samples_bp.route('/api/<int:sample_id>', methods=['PUT'])
@login_required
def api_update(sample_id):
    claims = get_jwt()
    data = request.json
    db = get_db()

    sample = db.execute("SELECT * FROM samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        
        return jsonify({'error': 'Sample not found'}), 404

    updates = []
    params = []
    for field in ['patient_name', 'patient_dob', 'patient_gender', 'priority', 'notes', 'client_id', 'estimated_turnaround']:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])

    if updates:
        params.append(sample_id)
        db.execute(f"UPDATE samples SET {', '.join(updates)} WHERE id = ?", params)

    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'sample', sample_id, 'Updated sample details', request.remote_addr)
    
    return jsonify({'message': 'Updated'})


@samples_bp.route('/api/<int:sample_id>/transition', methods=['POST'])
@login_required
def api_transition(sample_id):
    claims = get_jwt()
    data = request.json
    new_status = data.get('status')
    notes = data.get('notes', '')

    if new_status not in WORKFLOW and new_status != 'cancelled':
        return jsonify({'error': 'Invalid status'}), 400

    db = get_db()
    sample = db.execute("SELECT * FROM samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        
        return jsonify({'error': 'Sample not found'}), 404

    old_status = sample['status']

    if new_status == 'cancelled':
        if not notes:
            notes = 'Sample cancelled'
    elif new_status not in WORKFLOW_INDEX:
        
        return jsonify({'error': 'Invalid transition'}), 400
    else:
        if old_status == 'cancelled':
            
            return jsonify({'error': 'Cannot transition cancelled sample'}), 400

        old_idx = WORKFLOW_INDEX.get(old_status, -1)
        new_idx = WORKFLOW_INDEX[new_status]

        if new_idx != old_idx + 1 and new_status != 'registered':
            
            return jsonify({'error': f'Cannot go from {old_status} to {new_status}'}), 400

        allowed = STAGE_ROLES.get(new_status, [])
        if allowed and claims['role'] not in allowed:
            
            return jsonify({'error': 'Insufficient permissions for this transition'}), 403

    col_map = {
        'triaged': ('triaged_at', 'triaged_by'),
        'analysis': ('analyzed_at', 'analyzed_by'),
        'review': ('reviewed_at', 'reviewed_by'),
        'approved': ('approved_at', 'approved_by'),
        'reported': ('reported_at', 'reported_by'),
    }
    timestamp_col, user_col = col_map.get(new_status, (None, None))

    update_fields = ["status = ?"]
    params = [new_status]

    if new_status == 'cancelled':
        update_fields.append("cancelled_reason = ?")
        params.append(notes)
    else:
        if timestamp_col:
            update_fields.append(f"{timestamp_col} = CURRENT_TIMESTAMP")
        if user_col:
            update_fields.append(f"{user_col} = ?")
            params.append(claims['id'])

    if new_status == 'reported':
        update_fields.append("completed_at = CURRENT_TIMESTAMP")

    params.append(sample_id)
    db.execute(f"UPDATE samples SET {', '.join(update_fields)} WHERE id = ?", params)

    db.execute(
        "INSERT INTO sample_status_log (sample_id, from_status, to_status, user_id, username, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (sample_id, old_status, new_status, claims['id'], claims['username'], notes)
    )

    db.commit()
    log_audit(claims['id'], claims['username'], 'transition', 'sample', sample_id, f'{old_status} -> {new_status}', request.remote_addr)
    
    return jsonify({'message': f'Sample transitioned to {new_status}'})


@samples_bp.route('/api/<int:sample_id>/test', methods=['POST'])
@login_required
def api_add_test(sample_id):
    claims = get_jwt()
    data = request.json
    db = get_db()

    sample = db.execute("SELECT * FROM samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        
        return jsonify({'error': 'Sample not found'}), 404

    db.execute(
        "INSERT INTO sample_tests (sample_id, test_catalog_id, status) VALUES (?, ?, 'pending')",
        (sample_id, data['test_catalog_id'])
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'add_test', 'sample', sample_id, f'Added test ID {data["test_catalog_id"]}', request.remote_addr)
    
    return jsonify({'message': 'Test added'}), 201


@samples_bp.route('/api/<int:sample_id>/test/<int:test_id>', methods=['PUT'])
@login_required
def api_update_test(sample_id, test_id):
    claims = get_jwt()
    data = request.json
    db = get_db()

    tc = db.execute("SELECT * FROM test_catalog WHERE id = ?", (data.get('test_catalog_id') or 0,)).fetchone()

    updates = []
    params = []
    for field in ['result', 'unit', 'reference_range', 'notes', 'status', 'flagged']:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])

    if data.get('result') and tc and tc['ref_min'] is not None and tc['ref_max'] is not None:
        try:
            val = float(data['result'])
            if val < tc['ref_min'] or val > tc['ref_max']:
                updates.append("flagged = 1")
        except (ValueError, TypeError):
            pass

    if 'result' in data or 'status' in data:
        updates.append("performed_by = ?")
        params.append(claims['id'])
        updates.append("updated_at = CURRENT_TIMESTAMP")

    if updates:
        params.append(test_id)
        params.append(sample_id)
        db.execute(f"UPDATE sample_tests SET {', '.join(updates)} WHERE id = ? AND sample_id = ?", params)

    db.commit()
    log_audit(claims['id'], claims['username'], 'update_test', 'sample', sample_id, f'Updated test ID {test_id}', request.remote_addr)
    
    return jsonify({'message': 'Test updated'})


@samples_bp.route('/api/<int:sample_id>/test/<int:test_id>', methods=['DELETE'])
@login_required
def api_delete_test(sample_id, test_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM sample_tests WHERE id = ? AND sample_id = ?", (test_id, sample_id))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete_test', 'sample', sample_id, f'Deleted test ID {test_id}', request.remote_addr)
    
    return jsonify({'message': 'Test removed'})


@samples_bp.route('/api/types', methods=['GET'])
@login_required
def api_sample_types():
    db = get_db()
    rows = db.execute("SELECT * FROM sample_types WHERE active = 1 ORDER BY name").fetchall()
    
    return jsonify([dict(r) for r in rows])


@samples_bp.route('/api/catalog', methods=['GET'])
@login_required
def api_catalog():
    db = get_db()
    rows = db.execute("SELECT * FROM test_catalog WHERE active = 1 ORDER BY category, name").fetchall()
    
    return jsonify([dict(r) for r in rows])


@samples_bp.route('/api/clients', methods=['GET'])
@login_required
def api_clients():
    db = get_db()
    rows = db.execute("SELECT * FROM clients WHERE active = 1 ORDER BY name").fetchall()
    
    return jsonify([dict(r) for r in rows])
