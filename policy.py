"""Admission-policy experiment. Synthetic keys and a recording sink only."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
import threading
import time
from urllib.parse import urlsplit


MAX_BODY = 2048
# Public fixtures, deliberately not credentials from any applicant project.
KEYS = {"alice": b"public-fixture-alice", "bob": b"public-fixture-bob"}
SCOPES = {"alice": {"device-a"}, "bob": {"device-b"}}


def encode(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sign(raw: bytes, key_id: str = "alice") -> str:
    return hmac.new(KEYS[key_id], raw, hashlib.sha256).hexdigest()


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


@dataclass(frozen=True)
class Decision:
    status: int
    reason: str


class Policy:
    """Atomic replay/rate admission with an in-memory, non-network recording sink.

    `disabled` is for deliberate one-check ablations in the runner, never exposed
    by the HTTP handler. No security or persistence claim beyond this process.
    """

    def __init__(self, clock=time.time, disabled=frozenset()):
        self.clock = clock
        self.disabled = frozenset(disabled)
        self.lock = threading.Lock()
        self.seen = {}
        self.windows = {key: deque() for key in KEYS}
        self.effects = []

    def execute(self, raw: bytes, key_id: str, signature: str) -> Decision:
        if len(raw) > MAX_BODY:
            return Decision(413, "body_size")
        if (key_id not in KEYS or re.fullmatch(r"[0-9a-f]{64}", signature) is None
                or not hmac.compare_digest(sign(raw, key_id), signature)):
            return Decision(401, "authentication")
        try:
            obj = json.loads(raw, object_pairs_hook=no_duplicate_keys,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
        except (ValueError, UnicodeError, RecursionError):
            return Decision(400, "schema")
        fields = {"request_id", "timestamp", "tool", "resource", "url", "value"}
        if not isinstance(obj, dict) or set(obj) != fields:
            return Decision(400, "schema")
        if (not isinstance(obj["request_id"], str)
                or re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", obj["request_id"]) is None
                or type(obj["timestamp"]) is not int
                or any(not isinstance(obj[k], str) for k in ("tool", "resource", "url", "value"))
                or len(obj["value"]) > 256):
            return Decision(400, "schema")
        if obj["tool"] != "emit":
            return Decision(403, "tool")
        if "scope" not in self.disabled and obj["resource"] not in SCOPES[key_id]:
            return Decision(403, "scope")
        # Canonical origin/path gate. This does not fetch a URL or resolve DNS.
        try:
            target = urlsplit(obj["url"])
            allowed_url = (not any(ord(c) < 33 or ord(c) > 126 for c in obj["url"])
                           and target.scheme == "https" and target.hostname == "telemetry.example.test"
                           and target.port in (None, 443) and target.username is None
                           and target.password is None and target.path == "/ingest"
                           and not target.query and not target.fragment
                           and "\\" not in obj["url"])
        except ValueError:
            allowed_url = False
        if "url" not in self.disabled and not allowed_url:
            return Decision(403, "url")
        with self.lock:
            now = self.clock()
            if "freshness" not in self.disabled and abs(now - obj["timestamp"]) > 30:
                return Decision(403, "freshness")
            self.seen = {key: expiry for key, expiry in self.seen.items() if expiry > now}
            nonce = (key_id, obj["request_id"])
            if "replay" not in self.disabled and nonce in self.seen:
                return Decision(409, "replay")
            window = self.windows[key_id]
            while window and window[0] <= now - 2:
                window.popleft()
            if "rate" not in self.disabled and len(window) >= 3:
                return Decision(429, "rate")
            # Retain nonce beyond the last possible validity of a future-dated
            # request. Rejected requests do not consume the replay/rate budget.
            self.seen[nonce] = now + 61
            window.append(now)
            self.effects.append({"key_id": key_id, "request_id": obj["request_id"],
                                 "resource": obj["resource"], "value": obj["value"]})
        return Decision(200, "accepted")
