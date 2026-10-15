"""Serve the concept on localhost, excluding raw exports and project internals."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote
import argparse

ROOT = Path(__file__).resolve().parent
ALLOWED_ROOT = {'index.html','styles.css','app.js','favicon.svg'}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        path = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        resolved = (ROOT / path).resolve()
        allowed = path in ALLOWED_ROOT or path in ('data/dashboard.json','data/empty.json') or (path.startswith('assets/') and resolved.is_relative_to(ROOT/'assets'))
        if not allowed or not resolved.is_relative_to(ROOT) or not resolved.is_file():
            self.send_error(404,'Not found'); return
        super().do_GET()
    def do_HEAD(self):
        path = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        resolved = (ROOT/path).resolve()
        if not (path in ALLOWED_ROOT or path in ('data/dashboard.json','data/empty.json') or (path.startswith('assets/') and resolved.is_relative_to(ROOT/'assets'))) or not resolved.is_file():
            self.send_error(404,'Not found'); return
        super().do_HEAD()
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    print(f'Centripetal concept: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
