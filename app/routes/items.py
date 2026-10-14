from flask import Blueprint, request, jsonify, render_template
from app.database import get_db
from app.auth import login_required, log_audit
from flask_jwt_extended import get_jwt

items_bp = Blueprint('items', __name__, url_prefix='/items')

@items_bp.route('/', strict_slashes=False)
@login_required
def list_page():
    return render_template('items/list.html')

@items_bp.route('/form', strict_slashes=False)
@login_required
def form_page():
    return render_template('items/form.html')

@items_bp.route('/form/<int:item_id>')
@login_required
def edit_form_page(item_id):
    return render_template('items/form.html')

@items_bp.route('/api', methods=['GET'])
@login_required
def api_list():
    db = get_db()
    rows = db.execute("""SELECT i.*, s.name as supplier_name
        FROM items i LEFT JOIN suppliers s ON i.supplier_id = s.id
        ORDER BY i.name""").fetchall()
    return jsonify([dict(r) for r in rows])

@items_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    claims = get_jwt()
    data = request.json
    db = get_db()
    cursor = db.execute(
        "INSERT INTO items (name, category, sku, unit, price, cost, quantity, min_quantity, supplier_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data['name'], data.get('category'), data.get('sku'), data.get('unit', 'pcs'), data.get('price', 0), data.get('cost', 0), data.get('quantity', 0), data.get('min_quantity', 0), data.get('supplier_id'))
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'create', 'item', cursor.lastrowid, f'Created item: {data["name"]}', request.remote_addr)
    return jsonify({'id': cursor.lastrowid}), 201

@items_bp.route('/api/<int:item_id>', methods=['GET'])
@login_required
def api_get(item_id):
    db = get_db()
    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))

@items_bp.route('/api/<int:item_id>', methods=['PUT'])
@login_required
def api_update(item_id):
    claims = get_jwt()
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE items SET name=?, category=?, sku=?, unit=?, price=?, cost=?, quantity=?, min_quantity=?, supplier_id=?, active=? WHERE id=?",
        (data['name'], data.get('category'), data.get('sku'), data.get('unit', 'pcs'), data.get('price', 0), data.get('cost', 0), data.get('quantity', 0), data.get('min_quantity', 0), data.get('supplier_id'), data.get('active', 1), item_id)
    )
    db.commit()
    log_audit(claims['id'], claims['username'], 'update', 'item', item_id, f'Updated item: {data["name"]}', request.remote_addr)
    return jsonify({'message': 'Updated'})

@items_bp.route('/api/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete(item_id):
    claims = get_jwt()
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    log_audit(claims['id'], claims['username'], 'delete', 'item', item_id, 'Deleted item', request.remote_addr)
    return jsonify({'message': 'Deleted'})
