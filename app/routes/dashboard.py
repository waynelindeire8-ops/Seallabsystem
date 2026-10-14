from flask import Blueprint, jsonify, render_template
from app.database import get_db
from app.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard', strict_slashes=False)
@login_required
def dashboard_page():
    return render_template('dashboard.html')


@dashboard_bp.route('/dashboard/api/stats')
@login_required
def api_stats():
    db = get_db()

    total = db.execute("SELECT COUNT(*) c FROM samples").fetchone()['c']
    total_tests = db.execute("SELECT COUNT(*) c FROM sample_tests").fetchone()['c']
    test_parameters = db.execute("SELECT COUNT(*) c FROM test_catalog WHERE active = 1").fetchone()['c']
    clinics = db.execute("SELECT COUNT(*) c FROM clients WHERE active = 1").fetchone()['c']
    specimens = db.execute("SELECT COUNT(*) c FROM sample_types WHERE active = 1").fetchone()['c']
    patients = db.execute("SELECT COUNT(DISTINCT patient_name) c FROM samples").fetchone()['c']
    products = db.execute("SELECT COUNT(*) c FROM test_catalog WHERE active = 1").fetchone()['c']

    registered = db.execute("SELECT COUNT(*) c FROM samples WHERE status='registered'").fetchone()['c']
    triaged = db.execute("SELECT COUNT(*) c FROM samples WHERE status='triaged'").fetchone()['c']
    analysis = db.execute("SELECT COUNT(*) c FROM samples WHERE status='analysis'").fetchone()['c']
    review = db.execute("SELECT COUNT(*) c FROM samples WHERE status='review'").fetchone()['c']
    approved = db.execute("SELECT COUNT(*) c FROM samples WHERE status='approved'").fetchone()['c']
    reported = db.execute("SELECT COUNT(*) c FROM samples WHERE status='reported'").fetchone()['c']
    cancelled = db.execute("SELECT COUNT(*) c FROM samples WHERE status='cancelled'").fetchone()['c']
    urgent = db.execute("SELECT COUNT(*) c FROM samples WHERE priority='urgent' AND status NOT IN ('reported','cancelled')").fetchone()['c']

    avg_turnaround = db.execute(
        "SELECT AVG(CAST((julianday(completed_at) - julianday(created_at)) * 24 AS INTEGER)) avg_hrs FROM samples WHERE completed_at IS NOT NULL"
    ).fetchone()['avg_hrs'] or 0

    recent = db.execute(
        """SELECT s.*, st.name as type_name
           FROM samples s LEFT JOIN sample_types st ON s.sample_type_id = st.id
           ORDER BY s.created_at DESC LIMIT 10"""
    ).fetchall()

    samples_by_type = db.execute(
        """SELECT st.name, COUNT(*) c FROM samples s
           JOIN sample_types st ON s.sample_type_id = st.id
           GROUP BY st.name ORDER BY c DESC"""
    ).fetchall()

    samples_by_status = db.execute(
        "SELECT status, COUNT(*) c FROM samples GROUP BY status ORDER BY c DESC"
    ).fetchall()

    monthly = db.execute(
        """SELECT strftime('%Y-%m', created_at) as month, COUNT(*) c
           FROM samples WHERE created_at >= date('now', '-6 months')
           GROUP BY month ORDER BY month"""
    ).fetchall()

    db.close()

    return jsonify({
        'total': total,
        'total_tests': total_tests,
        'test_parameters': test_parameters,
        'clinics': clinics,
        'specimens': specimens,
        'patients': patients,
        'products': products,
        'registered': registered,
        'triaged': triaged,
        'analysis': analysis,
        'review': review,
        'approved': approved,
        'reported': reported,
        'cancelled': cancelled,
        'urgent': urgent,
        'avg_turnaround': avg_turnaround,
        'recent': [dict(r) for r in recent],
        'by_type': [{'name': r['name'], 'count': r['c']} for r in samples_by_type],
        'by_status': [{'status': r['status'], 'count': r['c']} for r in samples_by_status],
        'monthly': [{'month': r['month'], 'count': r['c']} for r in monthly],
    })
