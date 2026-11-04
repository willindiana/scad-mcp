import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .generate import generate as _generate, resolve_params
from .registry import load_registry, merge_user_presets

mcp = MCPServer("scad-mcp")
REGISTRY = load_registry()  # fail fast on a bad manifest
if _presets_file := os.environ.get("SCAD_PRESETS_FILE"):
    REGISTRY = merge_user_presets(REGISTRY, Path(_presets_file))  # fail fast on bad user presets


@mcp.tool()
def list_models() -> list[dict]:
    """List available parametric models with parameter schemas, presets, resolved defaults and licenses."""
    out = []
    for m in REGISTRY.values():
        d = m.model_dump(exclude={"entry"})
        d["defaults"] = resolve_params(m, {})
        out.append(d)
    return out


@mcp.tool()
def generate(model_id: str, params: dict | None = None, preset: str | None = None,
             allow_unknown_license: bool = False, preview: bool = False) -> dict:
    """Render STL and optionally PNG preview in artifacts dir. Preset defaults apply unless preset is given; per-call params override the preset. Unknown presets or params are rejected. Unknown licenses require allow_unknown_license=True. Returns artifact filename and STL metrics."""
    if model_id not in REGISTRY:
        raise ValueError(f"unknown model {model_id!r}; see list_models")
    return _generate(REGISTRY[model_id], {} if params is None else params,
                     allow_unknown_license, preview, preset)


def main():
    if os.environ.get("SCAD_MCP_TRANSPORT") == "http":
        from .http_auth import authenticated_app, read_key
        import uvicorn

        key = read_key()  # Fail startup if key missing, weak, or exposed.
        gateway_key = read_key(os.environ["SCAD_MCP_GATEWAY_KEY_FILE"]) if "SCAD_MCP_GATEWAY_KEY_FILE" in os.environ else None
        if gateway_key == key:
            raise ValueError("gateway API key must differ from existing client key")
        host = os.environ.get("SCAD_MCP_HOST", "0.0.0.0")
        app = mcp.streamable_http_app(host=host)
        app.add_middleware(authenticated_app, key=key, gateway_key=gateway_key)
        uvicorn.run(app, host=host, port=int(os.environ.get("SCAD_MCP_PORT", "8781")), access_log=False)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
