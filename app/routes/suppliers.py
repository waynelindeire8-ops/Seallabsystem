from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt

suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

@suppliers_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('suppliers/list.html')

@suppliers_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('suppliers/form.html')

@suppliers_bp.route('/form/<int:supplier_id>')
@login_required
def edit_form_page(supplier_id):
    return render_template('suppliers/form.html')

@suppliers_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])

@suppliers_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data.get('contact_person'), data.get('phone'), data.get('email'), data.get('address'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'supplier', cursor.lastrowid, f'Created supplier: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@suppliers_bp.route('/api/<int:supplier_id>', methods=['GET'])
@login_required
def api_get(supplier_id):
    db = get_db()
    row = db.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@suppliers_bp.route('/api/<int:supplier_id>', methods=['PUT'])
@login_required
def api_update(supplier_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE suppliers SET name=?, contact_person=?, phone=?, email=?, address=?, active=? WHERE id=?",
        (data['name'], data.get('contact_person'), data.get('phone'), data.get('email'), data.get('address'), data.get('active', 1), supplier_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'supplier', supplier_id, f'Updated supplier: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@suppliers_bp.route('/api/<int:supplier_id>', methods=['DELETE'])
@login_required
def api_delete(supplier_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'supplier', supplier_id, 'Deleted supplier', request.remote_addr)
    return jsonify({'message': 'Deleted'})
