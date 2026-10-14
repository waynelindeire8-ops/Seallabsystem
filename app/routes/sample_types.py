from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

sample_types_bp = Blueprint('sample_types', __name__, url_prefix='/sample-types')

@sample_types_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('sample_types/list.html')

@sample_types_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('sample_types/form.html')

@sample_types_bp.route('/form/<int:type_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(type_id):
    return render_template('sample_types/form.html')

@sample_types_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM sample_types ORDER BY name").fetchall()
    
    return jsonify([dict(r) for r in rows])

@sample_types_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO sample_types (name, storage_req, shelf_life_hrs, instructions) VALUES (?, ?, ?, ?)",
        (data['name'], data.get('storage_req'), data.get('shelf_life_hrs', 24), data.get('instructions'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'sample_type', cursor.lastrowid, f'Created type: {data["name"]}', request.remote_addr)
    
    return jsonify({'id': cursor.lastrowid}), 201

@sample_types_bp.route('/api/<int:type_id>', methods=['GET'])
@login_required
def api_get(type_id):
    db = get_db()
    row = db.execute("SELECT * FROM sample_types WHERE id = ?", (type_id,)).fetchone()
    
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@sample_types_bp.route('/api/<int:type_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(type_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE sample_types SET name=?, storage_req=?, shelf_life_hrs=?, instructions=?, active=? WHERE id=?",
        (data['name'], data.get('storage_req'), data.get('shelf_life_hrs', 24), data.get('instructions'), data.get('active', 1), type_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'sample_type', type_id, f'Updated type: {data["name"]}', request.remote_addr)
    
    return jsonify({'message': 'Updated'})

@sample_types_bp.route('/api/<int:type_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(type_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM sample_types WHERE id = ?", (type_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'sample_type', type_id, 'Deleted sample type', request.remote_addr)
    
    return jsonify({'message': 'Deleted'})
