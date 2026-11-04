"""Reject unauthenticated HTTP before MCP dispatch. No endpoint bypasses authentication."""
import hmac
import os
import stat
from pathlib import Path


def read_key(path: str | None = None) -> bytes:
    path = Path(path if path is not None else os.environ.get("SCAD_MCP_API_KEY_FILE", "/run/secrets/scad-mcp-api-key"))
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise PermissionError("scad-mcp API key file must be regular, owner-only, and owned by service user")
        key = source.read(4097)
    if not 32 <= len(key) <= 4096 or any(byte <= 32 or byte >= 127 for byte in key):
        raise ValueError("scad-mcp API key must be at least 32 printable ASCII bytes without whitespace")
    return key


def authenticated_app(app, key: bytes, gateway_key: bytes | None = None):
    keys = (key,) if gateway_key is None else (key, gateway_key)
    async def authenticate(scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await app(scope, receive, send)
            return
        headers = [value for name, value in scope.get("headers", []) if name.lower() == b"authorization"]
        if (len(headers) != 1 or not headers[0].startswith(b"Bearer ")
                or not any([hmac.compare_digest(headers[0][7:], candidate) for candidate in keys])):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain"), (b"cache-control", b"no-store")]})
                await send({"type": "http.response.body", "body": b"Unauthorized"})
            return
        await app(scope, receive, send)

    return authenticate
