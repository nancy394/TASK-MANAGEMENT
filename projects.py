from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_db, log_activity

bp = Blueprint("projects", __name__, url_prefix="/projects")


def get_project(pid):
    p = get_db().execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (pid, g.user["id"])).fetchone()
    if p is None:
        abort(404)
    return p


@bp.route("/")
@login_required
def list_projects():
    rows = get_db().execute(
        """SELECT p.*, COUNT(t.id) total, COALESCE(SUM(t.status='done'),0) done FROM projects p
           LEFT JOIN tasks t ON t.project_id = p.id WHERE p.user_id = ? GROUP BY p.id
           ORDER BY p.created_at DESC""", (g.user["id"],)).fetchall()
    return render_template("projects/list.html", projects=rows)


@bp.route("/new", methods=("GET", "POST"))
@bp.route("/<int:pid>/edit", methods=("GET", "POST"))
@login_required
def edit(pid=None):
    project = get_project(pid) if pid else None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        color = request.form.get("color", "#2563eb")
        if not name:
            flash("Project name is required.", "danger")
        else:
            db = get_db()
            if project:
                db.execute("UPDATE projects SET name=?, description=?, color=? WHERE id=?", (name, desc, color, pid))
                msg = f"Updated project '{name}'"
            else:
                cur = db.execute("INSERT INTO projects (user_id, name, description, color) VALUES (?,?,?,?)",
                                 (g.user["id"], name, desc, color))
                pid = cur.lastrowid
                msg = f"Created project '{name}'"
            db.commit()
            log_activity(g.user["id"], msg)
            flash(msg, "success")
            return redirect(url_for("projects.detail", pid=pid))
    return render_template("projects/form.html", project=project)


@bp.route("/<int:pid>")
@login_required
def detail(pid):
    project = get_project(pid)
    tasks = get_db().execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY status, due_date", (pid,)).fetchall()
    board = {s: [t for t in tasks if t["status"] == s] for s in ("todo", "in_progress", "done")}
    return render_template("projects/detail.html", project=project, board=board, total=len(tasks))


@bp.route("/<int:pid>/delete", methods=("POST",))
@login_required
def delete(pid):
    project = get_project(pid)
    db = get_db()
    db.execute("DELETE FROM projects WHERE id = ?", (pid,))
    db.commit()
    log_activity(g.user["id"], f"Deleted project '{project['name']}'")
    flash("Project deleted.", "info")
    return redirect(url_for("projects.list_projects"))
