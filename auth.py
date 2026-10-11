import functools
import re
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db, log_activity

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        error = None
        if not username or not email or not password:
            error = "All required fields must be filled."
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = "Invalid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        if error is None:
            db = get_db()
            exists = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
            if exists:
                error = "Username or email already registered."
            else:
                cur = db.execute(
                    "INSERT INTO users (username, email, full_name, password_hash) VALUES (?, ?, ?, ?)",
                    (username, email, full_name, generate_password_hash(password)),
                )
                uid = cur.lastrowid
                for name in ("Work", "Personal", "Learning"):
                    db.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (uid, name))
                db.commit()
                log_activity(uid, "Account created")
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("auth.login"))
        flash(error, "danger")
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username.lower())).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['full_name'] or user['username']}!", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
