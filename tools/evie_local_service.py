"""R22 EVIE localhost-only, read-only control-plane prototype.

HTTP is intentionally NOT an execution interface. No start, resume, signer,
nonce spend, worker dispatch, session-file access, publisher, CORS or browser UI.

Local bearer token is possession-based access only, not OS user identity or
mutually authenticated transport. Legacy direct CLIs remain accessible.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import stat
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.workflows.preflight import ROOT
from tools import evie_safe, evie_governed_flow, evie_execution_security

SCHEMA = "evie.local-readonly-service/1"
HOST = "127.0.0.1"
TOKEN_PATTERN = re.compile(r"^[a-f0-9]{64}$")
ROUTES = frozenset(("/v1/health", "/v1/policy", "/v1/plan", "/v1/security"))
MAX_RESPONSE = 48_000


def _token_path(filename: str, *, creating: bool) -> Path:
    file = Path(filename).expanduser().absolute()
    parent = file.parent
    if (not parent.is_dir() or parent.is_symlink()
            or parent.resolve().is_relative_to(ROOT.resolve())
            or file.resolve().is_relative_to(ROOT.resolve())
            or file.is_symlink() or file.is_dir()):
        raise ValueError("local token must be a regular file outside checkout")
    if creating and file.exists():
        raise ValueError("refusing existing bearer-token file")
    return file


def new_token_file(filename: str) -> Path:
    target = _token_path(filename, creating=True)
    data = (secrets.token_hex(32) + "\n").encode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def load_token(filename: str) -> str:
    target = _token_path(filename, creating=False)
    if not target.is_file() or target.stat().st_size > 128:
        raise ValueError("local service token missing or oversized")
    if os.name == "posix":
        metadata = target.stat()
        if metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ValueError("local token must not be group/world accessible")
        if metadata.st_uid != os.geteuid() or metadata.st_nlink != 1:
            raise ValueError("local token must be owned by service user and not hardlinked")
    try:
        token = target.read_text(encoding="ascii").strip()
    except UnicodeError as exc:
        raise ValueError("local token not ASCII") from exc
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("local token not a valid 256-bit hex secret")
    return token


def _data(route: str) -> dict:
    """Only reviewed read-only routes; never caller-provided paths."""
    if route == "/v1/health":
        return {
            "schemaVersion": SCHEMA, "service": "evie-local-readonly",
            "state": "ready_read_only", "boundInterface": HOST,
            "httpExecutionEndpointsEnabled": False, "publishingAuthorized": False,
            "signedLeaseConsumptionPossible": False,
            "authenticatedOSUser": False,
        }
    if route == "/v1/policy":
        return {
            "schemaVersion": SCHEMA, "mode": "source_only_policy",
            "data": evie_safe.policy_report(),
            "httpExecutionEndpointsEnabled": False,
            "publishingAuthorized": False,
        }
    if route == "/v1/plan":
        return {
            "schemaVersion": SCHEMA, "mode": "source_only_plan",
            "data": evie_governed_flow.plan(),
            "httpExecutionEndpointsEnabled": False,
            "publishingAuthorized": False,
        }
    if route == "/v1/security":
        return {
            "schemaVersion": SCHEMA, "mode": "read_only_security_contract",
            "data": evie_execution_security.assess(),
            "httpExecutionEndpointsEnabled": False,
            "publishingAuthorized": False,
        }
    raise ValueError("route not on read-only allowlist")


class LocalOnlyHTTPServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, port: int, token: str):
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("loopback port invalid")
        if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
            raise ValueError("local token invalid")
        self.expected_token = token
        super().__init__((HOST, port), LocalOnlyHandler)
        self.timeout = 2


class LocalOnlyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "EVIE-LocalReadOnly"
    sys_version = ""

    def log_message(self, *args):
        # No paths, tokens or header values written to logs.
        return

    def setup(self):
        super().setup()
        self.connection.settimeout(4)

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_RESPONSE:
            status = 503
            raw = b'{"error":"response-too-large","executionAuthorized":false}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(raw)

    def _reject(self, status: int, code: str) -> None:
        self._json(status, {
            "schemaVersion": SCHEMA, "error": code,
            "executionAuthorized": False, "publishingAuthorized": False,
        })

    def _boundary(self) -> bool:
        expected_host = f"{HOST}:{self.server.server_address[1]}"
        # Exact host check counters DNS rebinding/Host header confusion.
        if self.headers.get("Host") != expected_host:
            self._reject(403, "loopback-host-required")
            return False
        # Never grant a browser-origin route, even to a client holding the token.
        if (self.headers.get("Origin") is not None
                or self.headers.get("Referer") is not None):
            self._reject(403, "browser-origin-denied")
            return False
        expected = "Bearer " + self.server.expected_token
        supplied = self.headers.get("Authorization", "")
        if len(supplied) > 100 or not hmac.compare_digest(supplied, expected):
            self._reject(401, "local-bearer-required")
            return False
        return True

    def do_GET(self):
        if not self._boundary():
            return
        # Query arguments, fragments, trailing slash and session-path probes
        # are not part of the exact reviewed route set.
        if self.path not in ROUTES:
            self._reject(404, "route-not-allowlisted")
            return
        try:
            self._json(200, _data(self.path))
        except (OSError, TypeError, KeyError, ValueError, UnicodeError):
            self._reject(503, "source-inspection-unavailable")

    def do_HEAD(self):
        self._reject(405, "method-denied")

    def do_POST(self):
        self._reject(405, "method-denied")

    def do_PUT(self):
        self._reject(405, "method-denied")

    def do_PATCH(self):
        self._reject(405, "method-denied")

    def do_DELETE(self):
        self._reject(405, "method-denied")

    def do_OPTIONS(self):
        self._reject(405, "method-denied")

    def do_CONNECT(self):
        self._reject(405, "method-denied")

    def do_TRACE(self):
        self._reject(405, "method-denied")


def probe(*, port: int, token: str) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("probe needs bound port")
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("invalid local probe token")
    responses = {}
    for route in ("/v1/health", "/v1/plan", "/v1/policy", "/v1/security"):
        request = urllib.request.Request(
            f"http://{HOST}:{port}{route}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Bypass user proxy environment for any loopback probe.
        handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(handler)
        with opener.open(request, timeout=3) as conn:
            raw = conn.read(MAX_RESPONSE + 1)
            if conn.status != 200 or len(raw) > MAX_RESPONSE:
                raise ValueError("unexpected local response")
            responses[route] = json.loads(raw)
    if (responses["/v1/health"].get("httpExecutionEndpointsEnabled") is not False
            or responses["/v1/plan"].get("data", {}).get("nextStageExecuted") is not False
            or responses["/v1/plan"].get("publishingAuthorized") is not False
            or responses["/v1/security"].get("data", {}).get("executionAllowed") is not False
            or responses["/v1/security"].get("data", {}).get("promotionReady") is not False):
        # Neither the plan nor the security report may claim execution authority.
        raise ValueError("unexpected action-capable local service response")
    return {
        "schemaVersion": SCHEMA, "status": "read_only_loopback_probe_passed",
        "routeCount": len(responses),
        "sourcePlanState": responses["/v1/plan"]["data"]["state"],
        "executionAuthorized": False, "publishingAuthorized": False,
        "noLocalFilesWritten": True,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="R22 offline loopback read-only service; NO execution routes")
    actions = p.add_subparsers(dest="action", required=True)
    token = actions.add_parser("token", help="create an exclusive local 0600 token outside Git")
    token.add_argument("--token-file", required=True)
    serve = actions.add_parser("serve", help="run until interrupted on 127.0.0.1 only")
    serve.add_argument("--token-file", required=True)
    serve.add_argument("--port", type=int, default=8765)
    check = actions.add_parser("probe", help="read-only authenticated localhost probe")
    check.add_argument("--token-file", required=True)
    check.add_argument("--port", type=int, default=8765)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "token":
            new_token_file(args.token_file)
            result = {"schemaVersion": SCHEMA, "status": "token-file-created",
                      "tokenPrinted": False, "executionAuthorized": False}
        elif args.action == "probe":
            result = probe(port=args.port, token=load_token(args.token_file))
        else:
            token = load_token(args.token_file)
            with LocalOnlyHTTPServer(args.port, token) as server:
                # Deliberately never prints the token or accepts a bind address.
                print(json.dumps({
                    "schemaVersion": SCHEMA, "status": "serving_local_read_only",
                    "listen": f"{HOST}:{server.server_address[1]}",
                    "routes": sorted(ROUTES),
                    "executionAuthorized": False, "publishingAuthorized": False,
                }), flush=True)
                server.serve_forever(poll_interval=0.25)
            return 0
        print(json.dumps(result))
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError,
            urllib.error.URLError):
        print(json.dumps({
            "schemaVersion": SCHEMA, "status": "rejected",
            "executionAuthorized": False, "publishingAuthorized": False,
            "reason": "loopback-readonly-boundary-not-satisfied",
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
