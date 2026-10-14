from flask import Blueprint, render_template, jsonify, request
from app.database import get_db
from app.auth import login_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/', strict_slashes=False)
@login_required
def reports_page():
    return render_template('reports/index.html')

@reports_bp.route('/api/summary')
@login_required
def api_summary():
    db = get_db()
    period = request.args.get('period', 'month')

    if period == 'week':
        date_filter = "AND s.created_at >= date('now', '-7 days')"
    elif period == 'year':
        date_filter = "AND s.created_at >= date('now', '-12 months')"
    else:
        date_filter = "AND s.created_at >= date('now', '-30 days')"

    total = db.execute(f"SELECT COUNT(*) c FROM samples s WHERE 1=1 {date_filter}").fetchone()['c']
    by_status = db.execute(f"SELECT status, COUNT(*) c FROM samples s WHERE 1=1 {date_filter} GROUP BY status").fetchall()
    by_type = db.execute(f"""SELECT st.name, COUNT(*) c FROM samples s
        JOIN sample_types st ON s.sample_type_id = st.id WHERE 1=1 {date_filter} GROUP BY st.name ORDER BY c DESC""").fetchall()
    by_priority = db.execute(f"SELECT priority, COUNT(*) c FROM samples s WHERE 1=1 {date_filter} GROUP BY priority").fetchall()

    avg_turnaround = db.execute(f"""SELECT AVG(CAST((julianday(completed_at) - julianday(created_at)) * 24 AS INTEGER)) avg_hrs
        FROM samples s WHERE completed_at IS NOT NULL {date_filter}""").fetchone()['avg_hrs'] or 0

    daily = db.execute(f"""SELECT date(created_at) as day, COUNT(*) c FROM samples s
        WHERE 1=1 {date_filter} GROUP BY day ORDER BY day""").fetchall()

    top_clients = db.execute(f"""SELECT c.name, COUNT(*) c FROM samples s
        JOIN clients c ON s.client_id = c.id WHERE 1=1 {date_filter} GROUP BY c.name ORDER BY c DESC LIMIT 5""").fetchall()

    
    return jsonify({
        'total': total,
        'by_status': [{'status': r['status'], 'count': r['c']} for r in by_status],
        'by_type': [{'name': r['name'], 'count': r['c']} for r in by_type],
        'by_priority': [{'priority': r['priority'], 'count': r['c']} for r in by_priority],
        'avg_turnaround': avg_turnaround,
        'daily': [{'day': r['day'], 'count': r['c']} for r in daily],
        'top_clients': [{'name': r['name'], 'count': r['c']} for r in top_clients],
    })
