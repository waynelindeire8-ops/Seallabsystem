from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('clients/list.html')

@clients_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('clients/form.html')

@clients_bp.route('/form/<int:client_id>')
@login_required
def edit_form_page(client_id):
    return render_template('clients/form.html')

@clients_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    
    return jsonify([dict(r) for r in rows])

@clients_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO clients (name, contact_person, phone, email, address) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data.get('contact_person'), data.get('phone'), data.get('email'), data.get('address'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'client', cursor.lastrowid, f'Created client: {data["name"]}', request.remote_addr)
    
    return jsonify({'id': cursor.lastrowid}), 201

@clients_bp.route('/api/<int:client_id>', methods=['GET'])
@login_required
def api_get(client_id):
    db = get_db()
    row = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@clients_bp.route('/api/<int:client_id>', methods=['PUT'])
@login_required
def api_update(client_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE clients SET name=?, contact_person=?, phone=?, email=?, address=?, active=? WHERE id=?",
        (data['name'], data.get('contact_person'), data.get('phone'), data.get('email'), data.get('address'), data.get('active', 1), client_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'client', client_id, f'Updated client: {data["name"]}', request.remote_addr)
    
    return jsonify({'message': 'Updated'})

@clients_bp.route('/api/<int:client_id>', methods=['DELETE'])
@login_required
def api_delete(client_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'client', client_id, 'Deleted client', request.remote_addr)
    
    return jsonify({'message': 'Deleted'})
