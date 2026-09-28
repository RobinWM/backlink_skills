import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import threading

import pytest

if os.environ.get("RUN_AGENT_BROWSER_E2E") != "1":
    pytest.skip("agent-browser E2E is opt-in", allow_module_level=True)

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from agent_browser_adapter import AgentBrowserAdapter, AgentBrowserError

HTML = b"""<!doctype html><html><body>
<form method="post" action="/submitted" enctype="multipart/form-data">
<label>Product Name <input id="product-name" name="name"></label>
<label>Homepage <input id="homepage" name="homepage"></label>
<label>Readonly <input id="readonly" value="locked" readonly></label>
<label>Logo <input id="logo" type="file" name="logo"></label>
<label>Category <select id="category" name="category">
<option value="">Choose</option><option value="ai">AI Tools</option>
</select></label>
<label><input id="terms" type="checkbox"> Terms</label>
<button id="submit" type="submit">Submit</button>
</form></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = HTML if self.path.startswith("/form") else b"<h1>Submitted</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.send_response(303)
        self.send_header("Location", "/submitted")
        self.end_headers()

    def log_message(self, *args):
        return


@contextlib.contextmanager
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_real_agent_browser_form_flow(tmp_path):
    with server() as base:
        adapter = AgentBrowserAdapter(
            "e2e-form",
            env={"AGENT_BROWSER_ENCRYPTION_KEY": "1" * 64},
        )
        adapter.preflight()
        adapter.open(f"{base}/form", restore_check_url=f"{base}/**")
        assert adapter.safe_fill("#product-name", "ImgEnhancer") == "ImgEnhancer"
        assert adapter.safe_fill("#homepage", "https://imgenhancer.co") == "https://imgenhancer.co"
        with pytest.raises(AgentBrowserError, match="readonly"):
            adapter.safe_fill("#readonly", "no")
        logo = tmp_path / "logo.png"
        logo.write_bytes(b"non-empty")
        assert adapter.safe_upload("#logo", str(logo))
        assert adapter.safe_select("#category", ["AI Tools"]) == "ai"
        assert adapter.safe_check("#terms") is True
        adapter.click("#submit")
        adapter.wait_text("Submitted")
        assert adapter.get_url().endswith("/submitted")
        adapter.close()
