"""Web push notifications: subscription storage + due-task reminders.

Works even when the app tab is closed, because delivery goes through the
browser's push service to a service worker (static/sw.js).
"""
import json
import os
import threading
import time
from datetime import date

from flask import Blueprint, current_app, g, jsonify, request
from pywebpush import webpush, WebPushException

from auth import login_required
from db import get_db

bp = Blueprint("push", __name__)

VAPID_CLAIMS_SUB = "mailto:admin@taskflow.local"


def _vapid_keys():
    """Load or generate VAPID keys, persisted under the instance folder."""
    path = os.path.join(current_app.instance_path, "vapid.json")
    os.makedirs(current_app.instance_path, exist_ok=True)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    from py_vapid import Vapid

    v = Vapid()
    v.generate_keys()
    keys = {
        "private_key": v.private_pem().decode().strip(),
        "public_key": v.public_key_urlsafe,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(keys, f)
    return keys


@bp.get("/push/vapid-public-key")
@login_required
def vapid_public_key():
    return jsonify({"publicKey": _vapid_keys()["public_key"]})


@bp.post("/push/subscribe")
@login_required
def subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return jsonify({"error": "Invalid subscription"}), 400
    db = get_db()
    db.execute(
        """INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,
             p256dh=excluded.p256dh, auth=excluded.auth""",
        (g.user["id"], endpoint, keys["p256dh"], keys["auth"]),
    )
    db.commit()
    return jsonify({"ok": True})


@bp.post("/push/unsubscribe")
@login_required
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    if endpoint:
        db = get_db()
        db.execute(
            "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
            (g.user["id"], endpoint),
        )
        db.commit()
    return jsonify({"ok": True})


def send_push(user_id, title, body, url="/tasks"):
    """Send a push notification to every subscription of a user."""
    keys = _vapid_keys()
    db = get_db()
    subs = db.execute(
        "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    stale = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=keys["private_key"],
                vapid_claims={"sub": VAPID_CLAIMS_SUB},
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):  # subscription no longer valid
                stale.append(sub["endpoint"])
    for endpoint in stale:
        db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    db.commit()


def _due_reminders_once(app):
    """Notify users about tasks due today that haven't been reminded yet."""
    with app.app_context():
        db = get_db()
        today = date.today().isoformat()
        rows = db.execute(
            """SELECT t.id, t.user_id, t.title FROM tasks t
               WHERE t.due_date = ? AND t.status != 'done'
                 AND NOT EXISTS (
                   SELECT 1 FROM reminders_sent r
                   WHERE r.task_id = t.id AND r.reminder_date = ?)""",
            (today, today),
        ).fetchall()
        for row in rows:
            try:
                send_push(
                    row["user_id"],
                    "Task due today",
                    f"“{row['title']}” is due today.",
                    url=f"/tasks/{row['id']}",
                )
                db.execute(
                    "INSERT OR IGNORE INTO reminders_sent (task_id, reminder_date) VALUES (?, ?)",
                    (row["id"], today),
                )
                db.commit()
            except Exception:
                current_app.logger.exception("Failed to send due-task reminder")


def start_reminder_scheduler(app, interval_seconds=300):
    """Background loop checking for due tasks every `interval_seconds`."""
    def loop():
        while True:
            try:
                _due_reminders_once(app)
            except Exception:
                app.logger.exception("Reminder scheduler error")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=loop, name="due-reminders", daemon=True)
    thread.start()
    return thread
