from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

catalog_bp = Blueprint('catalog', __name__, url_prefix='/catalog')

@catalog_bp.route('/', strict_slashes=False)
@login_required
@role_required('lab_manager')
def list_page():
    return render_template('catalog/list.html')

@catalog_bp.route('/form', strict_slashes=False)
@login_required
@role_required('lab_manager')
def form_page():
    return render_template('catalog/form.html')

@catalog_bp.route('/form/<int:test_id>')
@login_required
@role_required('lab_manager')
def edit_form_page(test_id):
    return render_template('catalog/form.html')

@catalog_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM test_catalog ORDER BY category, name").fetchall()
    
    return jsonify([dict(r) for r in rows])

@catalog_bp.route('/api', methods=['POST'])
@login_required
@role_required('lab_manager')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO test_catalog (name, category, unit, ref_min, ref_max, reference_text, turnaround_hrs, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (data['name'], data['category'], data.get('unit'), data.get('ref_min'), data.get('ref_max'), data.get('reference_text'), data.get('turnaround_hrs', 24), data.get('price', 0))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'test_catalog', cursor.lastrowid, f'Created test: {data["name"]}', request.remote_addr)
    
    return jsonify({'id': cursor.lastrowid}), 201

@catalog_bp.route('/api/<int:test_id>', methods=['GET'])
@login_required
def api_get(test_id):
    db = get_db()
    row = db.execute("SELECT * FROM test_catalog WHERE id = ?", (test_id,)).fetchone()
    
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@catalog_bp.route('/api/<int:test_id>', methods=['PUT'])
@login_required
@role_required('lab_manager')
def api_update(test_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE test_catalog SET name=?, category=?, unit=?, ref_min=?, ref_max=?, reference_text=?, turnaround_hrs=?, price=?, active=? WHERE id=?",
        (data['name'], data['category'], data.get('unit'), data.get('ref_min'), data.get('ref_max'), data.get('reference_text'), data.get('turnaround_hrs', 24), data.get('price', 0), data.get('active', 1), test_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'test_catalog', test_id, f'Updated test: {data["name"]}', request.remote_addr)
    
    return jsonify({'message': 'Updated'})

@catalog_bp.route('/api/<int:test_id>', methods=['DELETE'])
@login_required
@role_required('lab_manager')
def api_delete(test_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM test_catalog WHERE id = ?", (test_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'test_catalog', test_id, 'Deleted test', request.remote_addr)
    
    return jsonify({'message': 'Deleted'})
