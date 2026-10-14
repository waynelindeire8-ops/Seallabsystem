from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt
from datetime import datetime

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

def _generate_code(conn, prefix='SAL'):
    today = datetime.now().strftime('%Y%m%d')
    row = conn.execute("SELECT COUNT(*) c FROM sales WHERE sale_code LIKE ?", (f'{prefix}-{today}-%',)).fetchone()
    return f'{prefix}-{today}-{row["c"]+1:04d}'

@sales_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('sales/list.html')

@sales_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('sales/form.html')

@sales_bp.route('/form/<int:sale_id>')
@login_required
def edit_form_page(sale_id):
    return render_template('sales/form.html')

@sales_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT s.*, c.name as client_name
        FROM sales s LEFT JOIN clients c ON s.client_id = c.id
        ORDER BY s.created_at DESC""").fetchall()
    return jsonify([dict(r) for r in rows])

@sales_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    sale_code = _generate_code(db)
    cursor = db.execute(
        "INSERT INTO sales (sale_code, client_id, sale_date, subtotal, tax, total, status, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sale_code, data.get('client_id'), data.get('sale_date'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'pending'), data.get('notes'), claims['id'])
    )
    sale_id = cursor.lastrowid
    for item in data.get('items', []):
        db.execute(
            "INSERT INTO sale_items (sale_id, item_id, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
            (sale_id, item['item_id'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
        )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'sale', sale_id, f'Created sale: {sale_code}', request.remote_addr)
    return jsonify({'id': sale_id, 'sale_code': sale_code}), 201

@sales_bp.route('/api/<int:sale_id>', methods=['GET'])
@login_required
def api_get(sale_id):
    db = get_db()
    sale = db.execute("SELECT s.*, c.name as client_name FROM sales s LEFT JOIN clients c ON s.client_id = c.id WHERE s.id = ?", (sale_id,)).fetchone()
    if not sale: return jsonify({'error': 'Not found'}), 404
    items = db.execute("SELECT si.*, i.name as item_name FROM sale_items si JOIN items i ON si.item_id = i.id WHERE si.sale_id = ?", (sale_id,)).fetchall()
    return jsonify({'sale': dict(sale), 'items': [dict(i) for i in items]})

@sales_bp.route('/api/<int:sale_id>', methods=['PUT'])
@login_required
def api_update(sale_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE sales SET client_id=?, sale_date=?, subtotal=?, tax=?, total=?, status=?, notes=? WHERE id=?",
        (data.get('client_id'), data.get('sale_date'), data.get('subtotal', 0), data.get('tax', 0), data.get('total', 0), data.get('status', 'pending'), data.get('notes'), sale_id)
    )
    if 'items' in data:
        db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
        for item in data['items']:
            db.execute(
                "INSERT INTO sale_items (sale_id, item_id, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
                (sale_id, item['item_id'], item['quantity'], item['unit_price'], item.get('total', item['quantity'] * item['unit_price']))
            )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'sale', sale_id, 'Updated sale', request.remote_addr)
    return jsonify({'message': 'Updated'})

@sales_bp.route('/api/<int:sale_id>', methods=['DELETE'])
@login_required
def api_delete(sale_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
    db.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'sale', sale_id, 'Deleted sale', request.remote_addr)
    return jsonify({'message': 'Deleted'})
