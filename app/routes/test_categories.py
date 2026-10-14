from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

test_categories_bp = Blueprint('test_categories', __name__, url_prefix='/test-categories')

@test_categories_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('test_categories/list.html')

@test_categories_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('test_categories/form.html')

@test_categories_bp.route('/form/<int:cat_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(cat_id):
    return render_template('test_categories/form.html')

@test_categories_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT tc.*, tg.name as group_name
        FROM test_categories tc
        LEFT JOIN test_groups tg ON tc.group_id = tg.id
        ORDER BY tg.name, tc.name""").fetchall()
    return jsonify([dict(r) for r in rows])

@test_categories_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO test_categories (name, group_id, description) VALUES (?, ?, ?)",
        (data['name'], data.get('group_id'), data.get('description'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'test_category', cursor.lastrowid, f'Created test category: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@test_categories_bp.route('/api/<int:cat_id>', methods=['GET'])
@login_required
def api_get(cat_id):
    db = get_db()
    row = db.execute("SELECT * FROM test_categories WHERE id = ?", (cat_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@test_categories_bp.route('/api/<int:cat_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(cat_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE test_categories SET name=?, group_id=?, description=?, active=? WHERE id=?",
        (data['name'], data.get('group_id'), data.get('description'), data.get('active', 1), cat_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'test_category', cat_id, f'Updated test category: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@test_categories_bp.route('/api/<int:cat_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(cat_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM test_categories WHERE id = ?", (cat_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'test_category', cat_id, 'Deleted test category', request.remote_addr)
    return jsonify({'message': 'Deleted'})
