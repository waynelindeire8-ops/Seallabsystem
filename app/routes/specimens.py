from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

specimens_bp = Blueprint('specimens', __name__, url_prefix='/specimens')

@specimens_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('specimens/list.html')

@specimens_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('specimens/form.html')

@specimens_bp.route('/form/<int:spec_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(spec_id):
    return render_template('specimens/form.html')

@specimens_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM specimens ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])

@specimens_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO specimens (name, storage_req, shelf_life_hrs, instructions) VALUES (?, ?, ?, ?)",
        (data['name'], data.get('storage_req'), data.get('shelf_life_hrs', 24), data.get('instructions'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'specimen', cursor.lastrowid, f'Created specimen: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@specimens_bp.route('/api/<int:spec_id>', methods=['GET'])
@login_required
def api_get(spec_id):
    db = get_db()
    row = db.execute("SELECT * FROM specimens WHERE id = ?", (spec_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@specimens_bp.route('/api/<int:spec_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(spec_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE specimens SET name=?, storage_req=?, shelf_life_hrs=?, instructions=?, active=? WHERE id=?",
        (data['name'], data.get('storage_req'), data.get('shelf_life_hrs', 24), data.get('instructions'), data.get('active', 1), spec_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'specimen', spec_id, f'Updated specimen: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@specimens_bp.route('/api/<int:spec_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(spec_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM specimens WHERE id = ?", (spec_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'specimen', spec_id, 'Deleted specimen', request.remote_addr)
    return jsonify({'message': 'Deleted'})
