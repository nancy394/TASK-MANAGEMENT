from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from auth import login_required
from db import get_db, log_activity

bp = Blueprint("profile", __name__, url_prefix="/profile")


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "info":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            clash = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, g.user["id"])).fetchone()
            if not email or clash:
                flash("Email is empty or already in use.", "danger")
            else:
                db.execute("UPDATE users SET full_name = ?, email = ? WHERE id = ?", (full_name, email, g.user["id"]))
                db.commit()
                flash("Profile updated.", "success")
        elif action == "password":
            cur = request.form.get("current", "")
            new = request.form.get("new", "")
            if not check_password_hash(g.user["password_hash"], cur):
                flash("Current password is incorrect.", "danger")
            elif len(new) < 6:
                flash("New password must be at least 6 characters.", "danger")
            else:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.user["id"]))
                db.commit()
                log_activity(g.user["id"], "Changed password")
                flash("Password changed.", "success")
        return redirect(url_for("profile.index"))
    counts = db.execute("""SELECT (SELECT COUNT(*) FROM tasks WHERE user_id=:u) tasks,
                           (SELECT COUNT(*) FROM projects WHERE user_id=:u) projects,
                           (SELECT COUNT(*) FROM comments WHERE user_id=:u) comments""", {"u": g.user["id"]}).fetchone()
    return render_template("profile.html", counts=counts)
