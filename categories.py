from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_db

bp = Blueprint("categories", __name__, url_prefix="/categories")


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            db.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (g.user["id"], name))
            db.commit()
            flash("Category added.", "success")
        return redirect(url_for("categories.index"))
    rows = db.execute("""SELECT c.*, COUNT(t.id) task_count FROM categories c LEFT JOIN tasks t ON t.category_id = c.id
                         WHERE c.user_id = ? GROUP BY c.id ORDER BY c.name""", (g.user["id"],)).fetchall()
    return render_template("categories.html", categories=rows)


@bp.route("/<int:cid>/delete", methods=("POST",))
@login_required
def delete(cid):
    db = get_db()
    db.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cid, g.user["id"]))
    db.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("categories.index"))
