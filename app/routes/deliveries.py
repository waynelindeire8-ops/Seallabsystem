from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt
from datetime import datetime

deliveries_bp = Blueprint('deliveries', __name__, url_prefix='/deliveries')

def _generate_code(conn, prefix='DEL'):
    today = datetime.now().strftime('%Y%m%d')
    row = conn.execute("SELECT COUNT(*) c FROM deliveries WHERE delivery_code LIKE ?", (f'{prefix}-{today}-%',)).fetchone()
    return f'{prefix}-{today}-{row["c"]+1:04d}'

@deliveries_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('deliveries/list.html')

@deliveries_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('deliveries/form.html')

@deliveries_bp.route('/form/<int:delivery_id>')
@login_required
def edit_form_page(delivery_id):
    return render_template('deliveries/form.html')

@deliveries_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT d.*, c.name as client_name
        FROM deliveries d LEFT JOIN clients c ON d.client_id = c.id
        ORDER BY d.created_at DESC""").fetchall()
    return jsonify([dict(r) for r in rows])

@deliveries_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    delivery_code = _generate_code(db)
    cursor = db.execute(
        "INSERT INTO deliveries (delivery_code, client_id, delivery_date, status, tracking_number, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (delivery_code, data.get('client_id'), data.get('delivery_date'), data.get('status', 'pending'), data.get('tracking_number'), data.get('notes'), claims['id'])
    )
    delivery_id = cursor.lastrowid
    for item in data.get('items', []):
        db.execute(
            "INSERT INTO delivery_items (delivery_id, item_id, quantity, notes) VALUES (?, ?, ?, ?)",
            (delivery_id, item['item_id'], item['quantity'], item.get('notes'))
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'delivery', delivery_id, f'Created delivery: {delivery_code}', request.remote_addr)
    return jsonify({'id': delivery_id, 'delivery_code': delivery_code}), 201

@deliveries_bp.route('/api/<int:delivery_id>', methods=['GET'])
@login_required
def api_get(delivery_id):
    db = get_db()
    deliv = db.execute("SELECT d.*, c.name as client_name FROM deliveries d LEFT JOIN clients c ON d.client_id = c.id WHERE d.id = ?", (delivery_id,)).fetchone()
    if not deliv: return jsonify({'error': 'Not found'}), 404
    items = db.execute("SELECT di.*, i.name as item_name FROM delivery_items di JOIN items i ON di.item_id = i.id WHERE di.delivery_id = ?", (delivery_id,)).fetchall()
    return jsonify({'delivery': dict(deliv), 'items': [dict(i) for i in items]})

@deliveries_bp.route('/api/<int:delivery_id>', methods=['PUT'])
@login_required
def api_update(delivery_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE deliveries SET client_id=?, delivery_date=?, status=?, tracking_number=?, notes=? WHERE id=?",
        (data.get('client_id'), data.get('delivery_date'), data.get('status', 'pending'), data.get('tracking_number'), data.get('notes'), delivery_id)
    )
    if 'items' in data:
        db.execute("DELETE FROM delivery_items WHERE delivery_id = ?", (delivery_id,))
        for item in data['items']:
            db.execute(
                "INSERT INTO delivery_items (delivery_id, item_id, quantity, notes) VALUES (?, ?, ?, ?)",
                (delivery_id, item['item_id'], item['quantity'], item.get('notes'))
            )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'delivery', delivery_id, 'Updated delivery', request.remote_addr)
    return jsonify({'message': 'Updated'})

@deliveries_bp.route('/api/<int:delivery_id>', methods=['DELETE'])
@login_required
def api_delete(delivery_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM delivery_items WHERE delivery_id = ?", (delivery_id,))
    db.execute("DELETE FROM deliveries WHERE id = ?", (delivery_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'delivery', delivery_id, 'Deleted delivery', request.remote_addr)
    return jsonify({'message': 'Deleted'})
