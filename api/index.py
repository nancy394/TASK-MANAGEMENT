import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

class StripApiPrefix:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == '/api/index.py':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index.py/'):
            environ['PATH_INFO'] = path[len('/api/index.py'):]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = StripApiPrefix(app.wsgi_app)
