from datetime import datetime
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_db, log_activity

bp = Blueprint("tasks", __name__, url_prefix="/tasks")
STATUSES = ["todo", "in_progress", "done"]
PRIORITIES = ["low", "medium", "high", "urgent"]


def get_task(tid):
    t = get_db().execute(
        """SELECT t.*, p.name project_name, c.name category_name FROM tasks t
           LEFT JOIN projects p ON p.id = t.project_id LEFT JOIN categories c ON c.id = t.category_id
           WHERE t.id = ? AND t.user_id = ?""", (tid, g.user["id"])).fetchone()
    if t is None:
        abort(404)
    return t


def owned_id(table, value):
    if not value:
        return None
    row = get_db().execute(f"SELECT id FROM {table} WHERE id = ? AND user_id = ?", (value, g.user["id"])).fetchone()
    return row["id"] if row else None


@bp.route("/")
@login_required
def list_tasks():
    db = get_db()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    project = request.args.get("project", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "due")
    sql = """SELECT t.*, p.name project_name, p.color project_color, c.name category_name FROM tasks t
             LEFT JOIN projects p ON p.id = t.project_id LEFT JOIN categories c ON c.id = t.category_id
             WHERE t.user_id = ?"""
    params = [g.user["id"]]
    if q:
        sql += " AND (t.title LIKE ? OR t.description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if status in STATUSES:
        sql += " AND t.status = ?"; params.append(status)
    if priority in PRIORITIES:
        sql += " AND t.priority = ?"; params.append(priority)
    if project.isdigit():
        sql += " AND t.project_id = ?"; params.append(int(project))
    if category.isdigit():
        sql += " AND t.category_id = ?"; params.append(int(category))
    order = {
        "due": "t.due_date IS NULL, t.due_date",
        "priority": "CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
        "newest": "t.created_at DESC",
        "title": "t.title COLLATE NOCASE",
    }.get(sort, "t.due_date")
    sql += f" ORDER BY {order}"
    tasks = db.execute(sql, params).fetchall()
    projects = db.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY name", (g.user["id"],)).fetchall()
    categories = db.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY name", (g.user["id"],)).fetchall()
    return render_template("tasks/list.html", tasks=tasks, projects=projects, categories=categories,
                           statuses=STATUSES, priorities=PRIORITIES, args=request.args,
                           today=datetime.now().date().isoformat())


@bp.route("/new", methods=("GET", "POST"))
@bp.route("/<int:tid>/edit", methods=("GET", "POST"))
@login_required
def edit(tid=None):
    db = get_db()
    task = get_task(tid) if tid else None
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        status = f.get("status") if f.get("status") in STATUSES else "todo"
        priority = f.get("priority") if f.get("priority") in PRIORITIES else "medium"
        due = f.get("due_date") or None
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                due = None
        data = (owned_id("projects", f.get("project_id")), owned_id("categories", f.get("category_id")),
                title, f.get("description", "").strip(), status, priority, due)
        if not title:
            flash("Task title is required.", "danger")
        else:
            completed = datetime.now().isoformat(" ", "seconds") if status == "done" else None
            if task:
                db.execute("""UPDATE tasks SET project_id=?, category_id=?, title=?, description=?, status=?,
                              priority=?, due_date=?, completed_at=? WHERE id=?""", data + (completed, tid))
                msg = f"Updated task '{title}'"
            else:
                cur = db.execute("""INSERT INTO tasks (project_id, category_id, title, description, status, priority,
                                    due_date, completed_at, user_id) VALUES (?,?,?,?,?,?,?,?,?)""",
                                 data + (completed, g.user["id"]))
                tid = cur.lastrowid
                msg = f"Created task '{title}'"
            db.commit()
            log_activity(g.user["id"], msg)
            flash(msg, "success")
            return redirect(url_for("tasks.detail", tid=tid))
    projects = db.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY name", (g.user["id"],)).fetchall()
    categories = db.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY name", (g.user["id"],)).fetchall()
    preset_project = request.args.get("project", type=int)
    return render_template("tasks/form.html", task=task, projects=projects, categories=categories,
                           statuses=STATUSES, priorities=PRIORITIES, preset_project=preset_project)


@bp.route("/<int:tid>")
@login_required
def detail(tid):
    task = get_task(tid)
    db = get_db()
    subtasks = db.execute("SELECT * FROM subtasks WHERE task_id = ? ORDER BY id", (tid,)).fetchall()
    comments = db.execute("""SELECT c.*, u.username FROM comments c JOIN users u ON u.id = c.user_id
                             WHERE c.task_id = ? ORDER BY c.id""", (tid,)).fetchall()
    return render_template("tasks/detail.html", task=task, subtasks=subtasks, comments=comments)


@bp.route("/<int:tid>/status/<status>", methods=("POST",))
@login_required
def set_status(tid, status):
    task = get_task(tid)
    if status not in STATUSES:
        abort(400)
    completed = datetime.now().isoformat(" ", "seconds") if status == "done" else None
    db = get_db()
    db.execute("UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", (status, completed, tid))
    db.commit()
    log_activity(g.user["id"], f"Moved '{task['title']}' to {status.replace('_', ' ')}")
    if status == "done":
        flash(f"Task completed: {task['title']}", "complete")
    else:
        flash(f"'{task['title']}' moved to {status.replace('_', ' ')}.", "info")
    return redirect(request.referrer or url_for("tasks.detail", tid=tid))


@bp.route("/<int:tid>/delete", methods=("POST",))
@login_required
def delete(tid):
    task = get_task(tid)
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (tid,))
    db.commit()
    log_activity(g.user["id"], f"Deleted task '{task['title']}'")
    flash("Task deleted.", "info")
    return redirect(url_for("tasks.list_tasks"))


@bp.route("/<int:tid>/subtasks", methods=("POST",))
@login_required
def add_subtask(tid):
    get_task(tid)
    title = request.form.get("title", "").strip()
    if title:
        db = get_db()
        db.execute("INSERT INTO subtasks (task_id, title) VALUES (?, ?)", (tid, title))
        db.commit()
    return redirect(url_for("tasks.detail", tid=tid))


@bp.route("/<int:tid>/subtasks/<int:sid>/toggle", methods=("POST",))
@login_required
def toggle_subtask(tid, sid):
    get_task(tid)
    db = get_db()
    db.execute("UPDATE subtasks SET done = 1 - done WHERE id = ? AND task_id = ?", (sid, tid))
    db.commit()
    return redirect(url_for("tasks.detail", tid=tid))


@bp.route("/<int:tid>/subtasks/<int:sid>/delete", methods=("POST",))
@login_required
def delete_subtask(tid, sid):
    get_task(tid)
    db = get_db()
    db.execute("DELETE FROM subtasks WHERE id = ? AND task_id = ?", (sid, tid))
    db.commit()
    return redirect(url_for("tasks.detail", tid=tid))


@bp.route("/<int:tid>/comments", methods=("POST",))
@login_required
def add_comment(tid):
    task = get_task(tid)
    body = request.form.get("body", "").strip()
    if body:
        db = get_db()
        db.execute("INSERT INTO comments (task_id, user_id, body) VALUES (?, ?, ?)", (tid, g.user["id"], body))
        db.commit()
        log_activity(g.user["id"], f"Commented on '{task['title']}'")
    return redirect(url_for("tasks.detail", tid=tid))
