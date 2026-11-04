import pytest

from scad_mcp import generate, server
from scad_mcp.registry import load_registry


@pytest.mark.parametrize("license", [None, "", "Unlicensed", "GPL-3.0-or-later"])
def test_unknown_license_refused_before_render(monkeypatch, license):
    model = load_registry()["gridfinity_extended"].model_copy(update={"license": license})
    monkeypatch.setattr(generate, "build_preset", lambda *_: pytest.fail("render setup reached"))
    with pytest.raises(ValueError, match="unknown or missing license"):
        generate.generate(model, {})


def test_known_license_and_explicit_override(monkeypatch):
    model = load_registry()["gridfinity_extended"]
    calls = []

    def fake_preset(m, params, preset=None):
        calls.append((m.license, params))
        raise RuntimeError("passed license gate")

    monkeypatch.setattr(generate, "build_preset", fake_preset)
    with pytest.raises(RuntimeError, match="passed license gate"):
        generate.generate(model, {})
    unknown = model.model_copy(update={"license": None})
    with pytest.raises(RuntimeError, match="passed license gate"):
        generate.generate(unknown, {}, allow_unknown_license=True)
    with pytest.raises(ValueError, match="unknown or missing license"):
        generate.generate(unknown, {}, allow_unknown_license="true")
    assert calls == [("GPL-3.0", {}), (None, {})]


def test_server_passes_per_call_override(monkeypatch):
    model = load_registry()["gridfinity_extended"].model_copy(update={"license": None})
    monkeypatch.setitem(server.REGISTRY, model.id, model)
    monkeypatch.setattr(server, "_generate", lambda *args: args)
    assert server.generate(model.id, allow_unknown_license=True) == (model, {}, True, False, None)
    assert server.generate(model.id, preset="standard") == (model, {}, False, False, "standard")
