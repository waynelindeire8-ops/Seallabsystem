from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt
from werkzeug.security import generate_password_hash

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/', strict_slashes=False)
@login_required
@role_required('admin')
def list_page():
    return render_template('users/list.html')

@users_bp.route('/form', strict_slashes=False)
@login_required
@role_required('admin')
def form_page():
    return render_template('users/form.html')

@users_bp.route('/form/<int:user_id>')
@login_required
@role_required('admin')
def edit_form_page(user_id):
    return render_template('users/form.html')

@users_bp.route('/api', methods=['GET'])
@login_required
@role_required('admin')
def api_list():
    db = get_db()
    rows = db.execute("SELECT id, username, role, first_name, last_name, email, active, created_at FROM users ORDER BY first_name").fetchall()
    
    return jsonify([dict(r) for r in rows])

@users_bp.route('/api', methods=['POST'])
@login_required
@role_required('admin')
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()

    existing = db.execute("SELECT id FROM users WHERE username = ?", (data['username'],)).fetchone()
    if existing:
        
        return jsonify({'error': 'Username already exists'}), 400

    cursor = db.execute(
        "INSERT INTO users (username, password_hash, role, first_name, last_name, email) VALUES (?, ?, ?, ?, ?, ?)",
        (data['username'], generate_password_hash(data['password']), data['role'], data['first_name'], data['last_name'], data.get('email'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'user', cursor.lastrowid, f'Created user: {data["username"]}', request.remote_addr)
    
    return jsonify({'id': cursor.lastrowid}), 201

@users_bp.route('/api/<int:user_id>', methods=['GET'])
@login_required
@role_required('admin')
def api_get(user_id):
    db = get_db()
    row = db.execute("SELECT id, username, role, first_name, last_name, email, active, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@users_bp.route('/api/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_update(user_id):
    claims = get_jwt()
    data = request.json
    db = get_db()

    if data.get('password'):
        db.execute(
            "UPDATE users SET username=?, password_hash=?, role=?, first_name=?, last_name=?, email=?, active=? WHERE id=?",
            (data['username'], generate_password_hash(data['password']), data['role'], data['first_name'], data['last_name'], data.get('email'), data.get('active', 1), user_id)
        )
    else:
        db.execute(
            "UPDATE users SET username=?, role=?, first_name=?, last_name=?, email=?, active=? WHERE id=?",
            (data['username'], data['role'], data['first_name'], data['last_name'], data.get('email'), data.get('active', 1), user_id)
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'user', user_id, f'Updated user: {data["username"]}', request.remote_addr)
    
    return jsonify({'message': 'Updated'})

@users_bp.route('/api/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete(user_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'user', user_id, 'Deleted user', request.remote_addr)
    
    return jsonify({'message': 'Deleted'})
