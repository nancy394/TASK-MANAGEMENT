import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")
    DATABASE = os.path.join(BASE_DIR, "taskflow.db")
    RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
