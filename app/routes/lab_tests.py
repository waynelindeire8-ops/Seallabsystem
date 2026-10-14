from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

lab_tests_bp = Blueprint('lab_tests', __name__, url_prefix='/lab-tests')

@lab_tests_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('lab_tests/list.html')

@lab_tests_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('lab_tests/form.html')

@lab_tests_bp.route('/form/<int:test_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(test_id):
    return render_template('lab_tests/form.html')

@lab_tests_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT lt.*, tc.name as category_name, s.name as specimen_name
        FROM laboratory_tests lt
        LEFT JOIN test_categories tc ON lt.category_id = tc.id
        LEFT JOIN specimens s ON lt.specimen_id = s.id
        ORDER BY tc.name, lt.name""").fetchall()
    return jsonify([dict(r) for r in rows])

@lab_tests_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO laboratory_tests (name, category_id, specimen_id, turnaround_hrs, price, description) VALUES (?, ?, ?, ?, ?, ?)",
        (data['name'], data.get('category_id'), data.get('specimen_id'), data.get('turnaround_hrs', 24), data.get('price', 0), data.get('description'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'lab_test', cursor.lastrowid, f'Created lab test: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@lab_tests_bp.route('/api/<int:test_id>', methods=['GET'])
@login_required
def api_get(test_id):
    db = get_db()
    row = db.execute("""SELECT lt.*, tc.name as category_name, s.name as specimen_name
        FROM laboratory_tests lt
        LEFT JOIN test_categories tc ON lt.category_id = tc.id
        LEFT JOIN specimens s ON lt.specimen_id = s.id
        WHERE lt.id = ?""", (test_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@lab_tests_bp.route('/api/<int:test_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(test_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE laboratory_tests SET name=?, category_id=?, specimen_id=?, turnaround_hrs=?, price=?, description=?, active=? WHERE id=?",
        (data['name'], data.get('category_id'), data.get('specimen_id'), data.get('turnaround_hrs', 24), data.get('price', 0), data.get('description'), data.get('active', 1), test_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'lab_test', test_id, f'Updated lab test: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@lab_tests_bp.route('/api/<int:test_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(test_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM laboratory_tests WHERE id = ?", (test_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'lab_test', test_id, 'Deleted lab test', request.remote_addr)
    return jsonify({'message': 'Deleted'})
