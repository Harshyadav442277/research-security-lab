"""Loopback HTTP transport for the controlled policy experiment."""
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from policy import MAX_BODY, Policy


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64


def make_server(policy: Policy, port: int = 0):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def reply(self, status, reason):
            body = json.dumps({"reason": reason}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            # Send the response FIN before closing a rejected request whose
            # body was intentionally left unread (notably on Windows TCP).
            self.connection.shutdown(socket.SHUT_WR)
            self.close_connection = True

        def do_POST(self):
            self.connection.settimeout(3)
            if self.path != "/execute":
                return self.reply(404, "route")
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                return self.reply(400, "framing")
            if not lengths[0].isascii() or not lengths[0].isdigit():
                return self.reply(400, "framing")
            size = int(lengths[0]) if len(lengths[0]) < 10 else MAX_BODY + 1
            if size > MAX_BODY:
                return self.reply(413, "body_size")
            if self.headers.get("Content-Type", "") != "application/json":
                return self.reply(415, "content_type")
            for header in ("X-Key-Id", "X-Signature"):
                if len(self.headers.get_all(header, [])) != 1:
                    return self.reply(401, "authentication")
            try:
                raw = self.rfile.read(size)
            except (TimeoutError, OSError):
                return self.reply(400, "incomplete_body")
            if len(raw) != size:
                return self.reply(400, "incomplete_body")
            decision = policy.execute(raw, self.headers["X-Key-Id"], self.headers["X-Signature"])
            self.reply(decision.status, decision.reason)

    return Server(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    print("Synthetic experiment server: http://127.0.0.1:8080/execute", flush=True)
    with make_server(Policy(), 8080) as server:
        server.serve_forever()
