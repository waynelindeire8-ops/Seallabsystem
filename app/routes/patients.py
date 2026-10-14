from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt

patients_bp = Blueprint('patients', __name__, url_prefix='/patients')

@patients_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('patients/list.html')

@patients_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('patients/form.html')

@patients_bp.route('/form/<int:patient_id>')
@login_required
def edit_form_page(patient_id):
    return render_template('patients/form.html')

@patients_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    search = request.args.get('search', '')
    if search:
        rows = db.execute(
            "SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY name",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])

@patients_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO clients (name, contact_person, phone, email, address) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data.get('contact_person', data['name']), data.get('phone'), data.get('email'), data.get('address'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'patient', cursor.lastrowid, f'Created patient: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@patients_bp.route('/api/<int:patient_id>', methods=['GET'])
@login_required
def api_get(patient_id):
    db = get_db()
    row = db.execute("SELECT * FROM clients WHERE id = ?", (patient_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@patients_bp.route('/api/<int:patient_id>', methods=['PUT'])
@login_required
def api_update(patient_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE clients SET name=?, contact_person=?, phone=?, email=?, address=?, active=? WHERE id=?",
        (data['name'], data.get('contact_person', data['name']), data.get('phone'), data.get('email'), data.get('address'), data.get('active', 1), patient_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'patient', patient_id, f'Updated patient: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@patients_bp.route('/api/<int:patient_id>', methods=['DELETE'])
@login_required
def api_delete(patient_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM clients WHERE id = ?", (patient_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'patient', patient_id, 'Deleted patient', request.remote_addr)
    return jsonify({'message': 'Deleted'})
