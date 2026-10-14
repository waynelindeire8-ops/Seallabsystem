from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

test_groups_bp = Blueprint('test_groups', __name__, url_prefix='/test-groups')

@test_groups_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('test_groups/list.html')

@test_groups_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('test_groups/form.html')

@test_groups_bp.route('/form/<int:group_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(group_id):
    return render_template('test_groups/form.html')

@test_groups_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM test_groups ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])

@test_groups_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO test_groups (name, description) VALUES (?, ?)",
        (data['name'], data.get('description'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'test_group', cursor.lastrowid, f'Created test group: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@test_groups_bp.route('/api/<int:group_id>', methods=['GET'])
@login_required
def api_get(group_id):
    db = get_db()
    row = db.execute("SELECT * FROM test_groups WHERE id = ?", (group_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@test_groups_bp.route('/api/<int:group_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(group_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE test_groups SET name=?, description=?, active=? WHERE id=?",
        (data['name'], data.get('description'), data.get('active', 1), group_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'test_group', group_id, f'Updated test group: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@test_groups_bp.route('/api/<int:group_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(group_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM test_groups WHERE id = ?", (group_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'test_group', group_id, 'Deleted test group', request.remote_addr)
    return jsonify({'message': 'Deleted'})
