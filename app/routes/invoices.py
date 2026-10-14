from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt
from datetime import datetime

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

def _generate_code(conn, prefix='INV'):
    today = datetime.now().strftime('%Y%m%d')
    row = conn.execute("SELECT COUNT(*) c FROM invoices WHERE invoice_code LIKE ?", (f'{prefix}-{today}-%',)).fetchone()
    return f'{prefix}-{today}-{row["c"]+1:04d}'

@invoices_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('invoices/list.html')

@invoices_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('invoices/form.html')

@invoices_bp.route('/form/<int:invoice_id>')
@login_required
def edit_form_page(invoice_id):
    return render_template('invoices/form.html')

@invoices_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT inv.*, c.name as client_name
        FROM invoices inv LEFT JOIN clients c ON inv.client_id = c.id
        ORDER BY inv.created_at DESC""").fetchall()
    return jsonify([dict(r) for r in rows])

@invoices_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    invoice_code = _generate_code(db)
    cursor = db.execute(
        "INSERT INTO invoices (invoice_code, client_id, invoice_date, due_date, subtotal, tax, total, status, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (invoice_code, data.get('client_id'), data.get('invoice_date'), data.get('due_date'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'pending'), data.get('notes'), claims['id'])
    )
    invoice_id = cursor.lastrowid
    for item in data.get('items', []):
        db.execute(
            "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
            (invoice_id, item['description'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'invoice', invoice_id, f'Created invoice: {invoice_code}', request.remote_addr)
    return jsonify({'id': invoice_id, 'invoice_code': invoice_code}), 201

@invoices_bp.route('/api/<int:invoice_id>', methods=['GET'])
@login_required
def api_get(invoice_id):
    db = get_db()
    inv = db.execute("SELECT inv.*, c.name as client_name FROM invoices inv LEFT JOIN clients c ON inv.client_id = c.id WHERE inv.id = ?", (invoice_id,)).fetchone()
    if not inv: return jsonify({'error': 'Not found'}), 404
    items = db.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchall()
    return jsonify({'invoice': dict(inv), 'items': [dict(i) for i in items]})

@invoices_bp.route('/api/<int:invoice_id>', methods=['PUT'])
@login_required
def api_update(invoice_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE invoices SET client_id=?, invoice_date=?, due_date=?, subtotal=?, tax=?, total=?, status=?, notes=? WHERE id=?",
        (data.get('client_id'), data.get('invoice_date'), data.get('due_date'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'pending'), data.get('notes'), invoice_id)
    )
    if 'items' in data:
        db.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        for item in data['items']:
            db.execute(
                "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
                (invoice_id, item['description'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
            )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'invoice', invoice_id, 'Updated invoice', request.remote_addr)
    return jsonify({'message': 'Updated'})

@invoices_bp.route('/api/<int:invoice_id>', methods=['DELETE'])
@login_required
def api_delete(invoice_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'invoice', invoice_id, 'Deleted invoice', request.remote_addr)
    return jsonify({'message': 'Deleted'})
