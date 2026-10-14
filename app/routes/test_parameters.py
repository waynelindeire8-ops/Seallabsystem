from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

test_parameters_bp = Blueprint('test_parameters', __name__, url_prefix='/test-parameters')

@test_parameters_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('test_parameters/list.html')

@test_parameters_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('test_parameters/form.html')

@test_parameters_bp.route('/form/<int:param_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(param_id):
    return render_template('test_parameters/form.html')

@test_parameters_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT tp.*, lt.name as test_name
        FROM test_parameters tp
        LEFT JOIN laboratory_tests lt ON tp.test_id = lt.id
        ORDER BY lt.name, tp.name""").fetchall()
    return jsonify([dict(r) for r in rows])

@test_parameters_bp.route('/api/by-test/<int:test_id>', methods=['GET'])
@login_required
def api_by_test(test_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM test_parameters WHERE test_id = ? ORDER BY name", (test_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@test_parameters_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO test_parameters (test_id, name, unit, ref_min, ref_max, reference_text, decimal_places) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data['test_id'], data['name'], data.get('unit'), data.get('ref_min'), data.get('ref_max'), data.get('reference_text'), data.get('decimal_places', 1))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'test_parameter', cursor.lastrowid, f'Created parameter: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@test_parameters_bp.route('/api/<int:param_id>', methods=['GET'])
@login_required
def api_get(param_id):
    db = get_db()
    row = db.execute("SELECT * FROM test_parameters WHERE id = ?", (param_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@test_parameters_bp.route('/api/<int:param_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(param_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE test_parameters SET test_id=?, name=?, unit=?, ref_min=?, ref_max=?, reference_text=?, decimal_places=?, active=? WHERE id=?",
        (data['test_id'], data['name'], data.get('unit'), data.get('ref_min'), data.get('ref_max'), data.get('reference_text'), data.get('decimal_places', 1), data.get('active', 1), param_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'test_parameter', param_id, f'Updated parameter: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@test_parameters_bp.route('/api/<int:param_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(param_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM test_parameters WHERE id = ?", (param_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'test_parameter', param_id, 'Deleted parameter', request.remote_addr)
    return jsonify({'message': 'Deleted'})
