from flask import Blueprint, request, jsonify, render_template, redirect, make_response
from flask_jwt_extended import (
    create_access_token, get_jwt, get_jwt_identity,
    verify_jwt_in_request, set_access_cookies, unset_jwt_cookies
)
from functools import wraps
from werkzeug.security import check_password_hash
from app.database import get_db
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ROLE_HIERARCHY = {
    'admin': 100,
    'lab_manager': 80,
    'lab_tech': 60,
    'sample_collector': 50,
    'viewer': 40,
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            if request.path.startswith('/api') or request.headers.get('Accept') == 'application/json':
                return make_response(jsonify({'error': 'Unauthorized'}), 401)
            return redirect('/auth/login')
        return f(*args, **kwargs)
    return decorated

def role_required(min_role):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_level = ROLE_HIERARCHY.get(claims.get('role', ''), 0)
                required_level = ROLE_HIERARCHY.get(min_role, 0)
                if user_level < required_level:
                    if request.path.startswith('/api') or request.headers.get('Accept') == 'application/json':
                        return make_response(jsonify({'error': 'Insufficient permissions'}), 403)
                    return redirect('/auth/login')
            except Exception:
                if request.path.startswith('/api') or request.headers.get('Accept') == 'application/json':
                    return make_response(jsonify({'error': 'Unauthorized'}), 401)
                return redirect('/auth/login')
            return f(*args, **kwargs)
        return decorated
    return wrapper

def log_audit(user_id, username, action, resource_type=None, resource_id=None, details=None, ip_address=None):
    db = get_db()
    db.execute(
        "INSERT INTO audit_logs (user_id, username, action, resource_type, resource_id, details, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, action, resource_type, resource_id, details, ip_address)
    )
    db.commit()


@auth_bp.route('/login', strict_slashes=False)
def login_page():
    return render_template('login.html')


@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1",
        (data['username'],)
    ).fetchone()
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_access_token(
        identity=str(user['id']),
        additional_claims={
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
        }
    )

    log_audit(user['id'], user['username'], 'login', 'user', user['id'], 'User logged in', request.remote_addr)

    resp = jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
        }
    })
    set_access_cookies(resp, token)
    return resp


@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    resp = jsonify({'message': 'Logged out'})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route('/api/me', methods=['GET'])
@login_required
def api_me():
    claims = get_jwt()
    return jsonify({
        'id': claims['id'],
        'username': claims['username'],
        'role': claims['role'],
        'first_name': claims['first_name'],
        'last_name': claims['last_name'],
    })
