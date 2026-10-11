import os
from flask import Flask, render_template
from config import Config
import db
import sounds
import auth, dashboard, projects, tasks, categories, reports, profile, focus, push


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    sounds.ensure_sounds(app.static_folder)
    os.makedirs(app.config["RECORDINGS_DIR"], exist_ok=True)
    if not app.config.get("TESTING"):
        push.start_reminder_scheduler(app)
    for module in (auth, dashboard, projects, tasks, categories, reports, profile, focus, push):
        app.register_blueprint(module.bp)

    @app.template_filter("label")
    def label(value):
        return (value or "").replace("_", " ").title()

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found"), 404

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, message="Bad request"), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
