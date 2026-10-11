from datetime import date
from flask import Blueprint, g, render_template
from auth import login_required
from db import get_db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    db = get_db()
    uid = g.user["id"]
    today = date.today().isoformat()
    stats = db.execute(
        """SELECT COUNT(*) total,
           SUM(status='todo') todo, SUM(status='in_progress') in_progress, SUM(status='done') done,
           SUM(status!='done' AND due_date IS NOT NULL AND due_date < ?) overdue
           FROM tasks WHERE user_id = ?""", (today, uid)).fetchone()
    upcoming = db.execute(
        """SELECT t.*, p.name project_name FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
           WHERE t.user_id = ? AND t.status != 'done' AND t.due_date IS NOT NULL
           ORDER BY t.due_date LIMIT 6""", (uid,)).fetchall()
    projects = db.execute(
        """SELECT p.*, COUNT(t.id) total, SUM(t.status='done') done FROM projects p
           LEFT JOIN tasks t ON t.project_id = p.id WHERE p.user_id = ? GROUP BY p.id
           ORDER BY p.created_at DESC LIMIT 4""", (uid,)).fetchall()
    activity = db.execute("SELECT * FROM activity WHERE user_id = ? ORDER BY id DESC LIMIT 8", (uid,)).fetchall()
    total = stats["total"] or 0
    pct = round((stats["done"] or 0) * 100 / total) if total else 0
    return render_template("dashboard.html", stats=stats, upcoming=upcoming, projects=projects,
                           activity=activity, pct=pct, today=today)
