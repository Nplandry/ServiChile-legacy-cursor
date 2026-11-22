

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE_404 = ROOT / "404.html"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_error(self, code, message=None, explain=None):
        if code != 404 or not PAGE_404.is_file():
            return super().send_error(code, message, explain)
        try:
            body = PAGE_404.read_bytes()
        except OSError:
            return super().send_error(code, message, explain)
        self.send_response(404, "Not Found")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt, *args):

        if args and str(args[0]).startswith("404"):
            super().log_message(fmt, *args)

def main() -> None:
    parser = argparse.ArgumentParser(description="ServiChile frontend con 404 propio")
    parser.add_argument("port", nargs="?", type=int, default=5500)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"ServiChile frontend: http://localhost:{args.port}/index.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")

if __name__ == "__main__":
    main()
