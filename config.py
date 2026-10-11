import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# On Vercel, only /tmp is writable. Locally, use project folder.
IS_VERCEL = os.environ.get("VERCEL") == "1"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")
    DATABASE = os.path.join("/tmp", "taskflow.db") if IS_VERCEL else os.path.join(BASE_DIR, "taskflow.db")
    RECORDINGS_DIR = os.path.join("/tmp", "recordings") if IS_VERCEL else os.path.join(BASE_DIR, "recordings")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
