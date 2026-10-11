import csv
import io
from datetime import date, timedelta
from flask import Blueprint, Response, g, render_template
from auth import login_required
from db import get_db

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
def index():
    db = get_db()
    uid = g.user["id"]
    by_priority = db.execute("""SELECT priority, COUNT(*) n FROM tasks WHERE user_id = ? GROUP BY priority""", (uid,)).fetchall()
    by_status = db.execute("""SELECT status, COUNT(*) n FROM tasks WHERE user_id = ? GROUP BY status""", (uid,)).fetchall()
    by_project = db.execute("""SELECT COALESCE(p.name, 'No project') name, COUNT(t.id) total,
                               COALESCE(SUM(t.status='done'),0) done FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
                               WHERE t.user_id = ? GROUP BY p.id ORDER BY total DESC""", (uid,)).fetchall()
    week = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        n = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND date(completed_at) = ?", (uid, d)).fetchone()[0]
        week.append((d[5:], n))
    max_week = max([n for _, n in week] + [1])
    total = sum(r["n"] for r in by_status) or 1
    return render_template("reports.html", by_priority=by_priority, by_status=by_status,
                           by_project=by_project, week=week, max_week=max_week, total=total)


@bp.route("/export.csv")
@login_required
def export_csv():
    rows = get_db().execute("""SELECT t.id, t.title, t.status, t.priority, t.due_date, p.name project, c.name category,
                               t.created_at, t.completed_at FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
                               LEFT JOIN categories c ON c.id = t.category_id WHERE t.user_id = ? ORDER BY t.id""",
                            (g.user["id"],)).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Title", "Status", "Priority", "Due date", "Project", "Category", "Created", "Completed"])
    for r in rows:
        w.writerow(list(r))
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=tasks.csv"})
