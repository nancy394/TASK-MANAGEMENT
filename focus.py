import os
import uuid
from flask import (Blueprint, abort, current_app, flash, g, jsonify, redirect,
                   render_template, request, send_from_directory, url_for)
from auth import login_required
from db import get_db, log_activity

bp = Blueprint("focus", __name__, url_prefix="/focus")
MODES = ("focus", "short_break", "long_break")
AUDIO_EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3", "audio/wav": "wav"}


def _int(value, default=0, lo=0, hi=10 ** 7):
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


@bp.route("/")
@login_required
def index():
    db = get_db()
    uid = g.user["id"]
    tasks = db.execute("SELECT id, title FROM tasks WHERE user_id = ? AND status != 'done' ORDER BY title", (uid,)).fetchall()
    sessions = db.execute("""SELECT f.*, t.title AS task_title FROM focus_sessions f
                             LEFT JOIN tasks t ON t.id = f.task_id
                             WHERE f.user_id = ? ORDER BY f.created_at DESC, f.id DESC LIMIT 50""", (uid,)).fetchall()
    stats = db.execute("""SELECT
        COALESCE(SUM(CASE WHEN mode='focus' THEN actual_seconds END),0) AS total_sec,
        COALESCE(SUM(CASE WHEN mode='focus' AND date(created_at)=date('now') THEN actual_seconds END),0) AS today_sec,
        COUNT(CASE WHEN mode='focus' AND completed=1 THEN 1 END) AS completed,
        COUNT(recording) AS recordings
        FROM focus_sessions WHERE user_id = ?""", (uid,)).fetchone()
    return render_template("focus.html", tasks=tasks, sessions=sessions, stats=stats,
                           preselect=request.args.get("task", type=int))


@bp.route("/record", methods=("POST",))
@login_required
def record():
    """Save a finished/stopped session, with an optional voice recording."""
    db = get_db()
    uid = g.user["id"]
    mode = request.form.get("mode", "focus")
    if mode not in MODES:
        return jsonify(error="Invalid mode"), 400
    planned = _int(request.form.get("planned_minutes"), 25, 1, 240)
    actual = _int(request.form.get("actual_seconds"), 0, 0, 240 * 60)
    completed = 1 if request.form.get("completed") == "1" else 0
    note = request.form.get("note", "").strip()[:500]
    task_id = _int(request.form.get("task_id"), 0) or None
    if task_id and not db.execute("SELECT 1 FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid)).fetchone():
        task_id = None

    filename = None
    audio = request.files.get("audio")
    if audio and audio.filename is not None:
        data = audio.read()
        if data:
            ext = AUDIO_EXT.get((audio.mimetype or "").split(";")[0], "webm")
            filename = f"{uid}_{uuid.uuid4().hex}.{ext}"
            with open(os.path.join(current_app.config["RECORDINGS_DIR"], filename), "wb") as f:
                f.write(data)

    db.execute("""INSERT INTO focus_sessions (user_id, task_id, mode, planned_minutes, actual_seconds, completed, note, recording)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (uid, task_id, mode, planned, actual, completed, note, filename))
    db.commit()
    if mode == "focus":
        log_activity(uid, f"Focus session: {actual // 60} min {'completed' if completed else 'stopped'}")
    return jsonify(ok=True)


@bp.route("/recording/<int:sid>")
@login_required
def recording(sid):
    row = get_db().execute("SELECT recording FROM focus_sessions WHERE id = ? AND user_id = ?",
                           (sid, g.user["id"])).fetchone()
    if not row or not row["recording"]:
        abort(404)
    return send_from_directory(current_app.config["RECORDINGS_DIR"], row["recording"])


@bp.route("/<int:sid>/delete", methods=("POST",))
@login_required
def delete(sid):
    db = get_db()
    row = db.execute("SELECT recording FROM focus_sessions WHERE id = ? AND user_id = ?", (sid, g.user["id"])).fetchone()
    if not row:
        abort(404)
    if row["recording"]:
        path = os.path.join(current_app.config["RECORDINGS_DIR"], row["recording"])
        if os.path.exists(path):
            os.remove(path)
    db.execute("DELETE FROM focus_sessions WHERE id = ?", (sid,))
    db.commit()
    flash("Session deleted.", "info")
    return redirect(url_for("focus.index"))
