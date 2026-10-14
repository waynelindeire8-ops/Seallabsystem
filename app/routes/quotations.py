from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt
from datetime import datetime

quotations_bp = Blueprint('quotations', __name__, url_prefix='/quotations')

def _generate_code(conn, prefix='QUO'):
    today = datetime.now().strftime('%Y%m%d')
    row = conn.execute("SELECT COUNT(*) c FROM quotations WHERE quote_code LIKE ?", (f'{prefix}-{today}-%',)).fetchone()
    return f'{prefix}-{today}-{row["c"]+1:04d}'

@quotations_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('quotations/list.html')

@quotations_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('quotations/form.html')

@quotations_bp.route('/form/<int:quote_id>')
@login_required
def edit_form_page(quote_id):
    return render_template('quotations/form.html')

@quotations_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT q.*, c.name as client_name
        FROM quotations q LEFT JOIN clients c ON q.client_id = c.id
        ORDER BY q.created_at DESC""").fetchall()
    return jsonify([dict(r) for r in rows])

@quotations_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    quote_code = _generate_code(db)
    cursor = db.execute(
        "INSERT INTO quotations (quote_code, client_id, quote_date, valid_until, subtotal, tax, total, status, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (quote_code, data.get('client_id'), data.get('quote_date'), data.get('valid_until'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'draft'), data.get('notes'), claims['id'])
    )
    quote_id = cursor.lastrowid
    for item in data.get('items', []):
        db.execute(
            "INSERT INTO quotation_items (quotation_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
            (quote_id, item['description'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'quotation', quote_id, f'Created quotation: {quote_code}', request.remote_addr)
    return jsonify({'id': quote_id, 'quote_code': quote_code}), 201

@quotations_bp.route('/api/<int:quote_id>', methods=['GET'])
@login_required
def api_get(quote_id):
    db = get_db()
    q = db.execute("SELECT q.*, c.name as client_name FROM quotations q LEFT JOIN clients c ON q.client_id = c.id WHERE q.id = ?", (quote_id,)).fetchone()
    if not q: return jsonify({'error': 'Not found'}), 404
    items = db.execute("SELECT * FROM quotation_items WHERE quotation_id = ?", (quote_id,)).fetchall()
    return jsonify({'quotation': dict(q), 'items': [dict(i) for i in items]})

@quotations_bp.route('/api/<int:quote_id>', methods=['PUT'])
@login_required
def api_update(quote_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE quotations SET client_id=?, quote_date=?, valid_until=?, subtotal=?, tax=?, total=?, status=?, notes=? WHERE id=?",
        (data.get('client_id'), data.get('quote_date'), data.get('valid_until'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'draft'), data.get('notes'), quote_id)
    )
    if 'items' in data:
        db.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quote_id,))
        for item in data['items']:
            db.execute(
                "INSERT INTO quotation_items (quotation_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
                (quote_id, item['description'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
            )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'quotation', quote_id, 'Updated quotation', request.remote_addr)
    return jsonify({'message': 'Updated'})

@quotations_bp.route('/api/<int:quote_id>', methods=['DELETE'])
@login_required
def api_delete(quote_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quote_id,))
    db.execute("DELETE FROM quotations WHERE id = ?", (quote_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'quotation', quote_id, 'Deleted quotation', request.remote_addr)
    return jsonify({'message': 'Deleted'})
