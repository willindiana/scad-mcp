import asyncio
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from scad_mcp import http_auth, server


async def request(app, headers):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app({"type": "http", "method": "GET", "path": "/mcp", "headers": headers}, receive, send)
    return sent


def test_key_file_permissions_and_startup_refusal(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "key"
        monkeypatch.setenv("SCAD_MCP_API_KEY_FILE", str(path))
        with pytest.raises(FileNotFoundError):
            http_auth.read_key()
        path.write_text("strong-test-key-that-is-at-least-32-bytes")
        path.chmod(0o644)
        with pytest.raises(PermissionError):
            http_auth.read_key()
        path.chmod(0o600)
        assert http_auth.read_key() == b"strong-test-key-that-is-at-least-32-bytes"
        path.write_text("weak")
        with pytest.raises(ValueError):
            http_auth.read_key()
        path.write_text("strong-test-key-that-is-at-least-32-bytes")
        link = Path(temp) / "link"
        link.symlink_to(path)
        monkeypatch.setenv("SCAD_MCP_API_KEY_FILE", str(link))
        with pytest.raises(OSError):
            http_auth.read_key()


def test_http_refuses_before_dispatch_without_key():
    calls = []

    async def downstream(scope, receive, send):
        calls.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    key = b"strong-test-key-that-is-at-least-32-bytes"
    app = http_auth.authenticated_app(downstream, key)
    for headers in ([], [(b"authorization", b"Bearer wrong")],
                    [(b"authorization", b"Basic " + key)],
                    [(b"authorization", b"Bearer " + key), (b"Authorization", b"Bearer " + key)]):
        messages = asyncio.run(request(app, headers))
        assert messages[0]["status"] == 401
        assert calls == []
    messages = asyncio.run(request(app, [(b"Authorization", b"Bearer " + key)]))
    assert messages[0]["status"] == 200
    assert len(calls) == 1


def test_real_mcp_initialize_requires_auth():
    key = b"strong-test-key-that-is-at-least-32-bytes"
    app = server.mcp.streamable_http_app(host="0.0.0.0")
    app.add_middleware(http_auth.authenticated_app, key=key)
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                          "clientInfo": {"name": "test", "version": "1"}}}
    with TestClient(app) as client:
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            assert client.post("/mcp", json=payload, headers=headers).status_code == 401
        response = client.post("/mcp", json=payload,
                               headers={"Authorization": "Bearer " + key.decode(),
                                        "Accept": "application/json, text/event-stream"})
        assert response.status_code == 200
        assert '"name":"scad-mcp"' in response.text


def test_separate_gateway_key_and_revocation():
    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
    key, gateway = b"x" * 32, b"y" * 32
    for extra, candidate, expected in ((gateway, gateway, 200), (gateway, key, 200),
                                      (None, gateway, 401), (None, key, 200)):
        app = http_auth.authenticated_app(downstream, key, gateway_key=extra)
        messages = asyncio.run(request(app, [(b"authorization", b"Bearer " + candidate)]))
        assert messages[0]["status"] == expected


def test_oversized_key_rejected(tmp_path):
    path = tmp_path / "key"
    path.write_bytes(b"x" * 4097)
    path.chmod(0o600)
    with pytest.raises(ValueError):
        http_auth.read_key(str(path))
