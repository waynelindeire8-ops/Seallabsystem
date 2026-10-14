from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, role_required, log_audit
from flask_jwt_extended import get_jwt

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', strict_slashes=False)
@login_required
@role_required('admin')
def settings_page():
    return render_template('settings/system.html')

@settings_bp.route('/api/config', methods=['GET'])
@login_required
@role_required('admin')
def api_get_config():
    db = get_db()
    rows = db.execute("SELECT key, value FROM system_config").fetchall()
    
    return jsonify({r['key']: r['value'] for r in rows})

@settings_bp.route('/api/config', methods=['PUT'])
@login_required
@role_required('admin')
def api_update_config():
    claims = get_jwt()
    data = request.json
    db = get_db()
    for key, value in data.items():
        db.execute(
            "INSERT OR REPLACE INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'settings', None, 'Updated system config', request.remote_addr)
    
    return jsonify({'message': 'Settings saved'})
