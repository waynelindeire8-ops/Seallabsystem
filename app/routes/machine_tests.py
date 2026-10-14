from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

machine_tests_bp = Blueprint('machine_tests', __name__, url_prefix='/machine-tests')

@machine_tests_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('machine_tests/list.html')

@machine_tests_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('machine_tests/form.html')

@machine_tests_bp.route('/form/<int:machine_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(machine_id):
    return render_template('machine_tests/form.html')

@machine_tests_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT mt.*, lt.name as test_name
        FROM machine_tests mt
        LEFT JOIN laboratory_tests lt ON mt.test_id = lt.id
        ORDER BY mt.machine_name""").fetchall()
    return jsonify([dict(r) for r in rows])

@machine_tests_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO machine_tests (machine_name, test_id, machine_code, manufacturer, model, calibration_date, next_calibration, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data['machine_name'], data.get('test_id'), data.get('machine_code'), data.get('manufacturer'), data.get('model'), data.get('calibration_date'), data.get('next_calibration'), data.get('status', 'active'), data.get('notes'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'machine_test', cursor.lastrowid, f'Created machine: {data["machine_name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@machine_tests_bp.route('/api/<int:machine_id>', methods=['GET'])
@login_required
def api_get(machine_id):
    db = get_db()
    row = db.execute("""SELECT mt.*, lt.name as test_name
        FROM machine_tests mt
        LEFT JOIN laboratory_tests lt ON mt.test_id = lt.id
        WHERE mt.id = ?""", (machine_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@machine_tests_bp.route('/api/<int:machine_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(machine_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE machine_tests SET machine_name=?, test_id=?, machine_code=?, manufacturer=?, model=?, calibration_date=?, next_calibration=?, status=?, notes=? WHERE id=?",
        (data['machine_name'], data.get('test_id'), data.get('machine_code'), data.get('manufacturer'), data.get('model'), data.get('calibration_date'), data.get('next_calibration'), data.get('status', 'active'), data.get('notes'), machine_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'machine_test', machine_id, f'Updated machine: {data["machine_name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@machine_tests_bp.route('/api/<int:machine_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(machine_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM machine_tests WHERE id = ?", (machine_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'machine_test', machine_id, 'Deleted machine', request.remote_addr)
    return jsonify({'message': 'Deleted'})
