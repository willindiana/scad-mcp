import shutil
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from scad_mcp import generate as g
from scad_mcp.registry import load_registry
from scad_mcp.registry import Param

M = load_registry()["gridfinity_extended"]

STANDARD = {
    "width": "[1, 0]",
    "depth": "[1, 0]",
    "height": "[7, 0]",
    "lip_style": "normal",
    "wall_thickness": "0",
    "enable_magnets": "false",
    "enable_screws": "false",
    "fingerslide": "none",
    "label_style": "normal",
}

def test_defaults_and_mapping():
    assert g.build_preset(M, {}) == STANDARD
    assert g.build_preset(M, {"width": 4, "depth": 3, "height": 4})["width"] == "[4, 0]"

def test_explicit_preset_matches_default():
    assert g.build_preset(M, {}, preset="standard") == STANDARD

def test_per_call_params_override_preset():
    assert g.build_preset(M, {"width": 2, "height": 4}) == {
        **STANDARD, "width": "[2, 0]", "height": "[4, 0]"
    }

def test_resolve_params_returns_friendly_values():
    assert g.resolve_params(M, {}) == {
        "width": 1, "depth": 1, "height": 7,
        "lip_style": "normal", "wall_thickness": 0,
        "enable_magnets": False, "enable_screws": False,
        "fingerslide": "none", "label_style": "normal",
    }

def test_params_layer_over_manifest_defaults_without_a_preset():
    no_preset = M.model_copy(update={"default_preset": None})
    assert g.resolve_params(no_preset, {"label_style": "gflabel"})["height"] == 3
    assert g.build_preset(no_preset, {"label_style": "gflabel"})["label_style"] == "gflabel"

@pytest.mark.parametrize("preset", ["bogus", "", "STANDARD"])
def test_unknown_preset_rejected(preset):
    with pytest.raises(ValueError, match="unknown preset"):
        g.build_preset(M, {}, preset=preset)

@pytest.mark.parametrize("bad", [
    {"bogus": 1},                          # unknown key
    {"width": "4); cube(1e9"},             # code injection attempt
    {"width": "[4, 0]"},                   # raw SCAD literal
    {"width": 4.5},                        # float for int
    {"width": True},                       # bool is not int
    {"width": 0}, {"width": 11},           # out of range
    {"width": float("nan")}, {"width": float("inf")},
    {"width": None}, {"width": [4]},
    {"label_style": "normal; cube(100)"},  # unknown enum value
    {"enable_magnets": 1},                 # bool only
    {"wall_thickness": -0.1}, {"wall_thickness": 5.1},
])
def test_bad_params_rejected(bad):
    with pytest.raises(ValueError):
        g.build_preset(M, bad)

def test_enum_is_plain_string_for_customizer_json():
    p = Param(type="enum", default="x\"); cube(100); //", values=["x\"); cube(100); //"], scad_name="label")
    assert g._scad_value("label", p, p.default) == p.default

def test_params_must_be_object():
    with pytest.raises(ValueError):
        g.build_preset(M, ["width"])

@pytest.mark.parametrize("field,value", [
    ("scad_format", "{}); cube(999); //"),
    ("scad_name", "width; cube(999)"),
])
def test_manifest_cannot_inject_scad(field, value):
    with pytest.raises(ValidationError):
        Param.model_validate({"type": "int", "default": 1, "scad_name": "width", field: value})

def test_local_renderer_runs_without_docker(monkeypatch):
    monkeypatch.setattr(g, "RENDERER", "local")
    assert g._run_cmd(["openscad", "--version"], Path("/tmp/work")) == ["openscad", "--version"]
    monkeypatch.setattr(g, "RENDERER", "bogus")
    with pytest.raises(ValueError):
        g._run_cmd([], Path("/tmp/work"))


def test_renderer_uses_json_preset_never_defines(monkeypatch, tmp_path):
    import json
    import subprocess

    monkeypatch.setattr(g, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(g, "RENDERER", "local")
    calls = []

    def run(cmd, *, cwd, **kwargs):
        calls.append(cmd)
        assert "-D" not in cmd
        assert cmd[cmd.index("-p") + 1] == "preset.json"
        assert cmd[cmd.index("-P") + 1] == "p"
        data = json.loads((cwd / "preset.json").read_text())
        assert data == {"fileFormatVersion": "1", "parameterSets": {"p": STANDARD}}
        if "preview.png" in cmd:
            (cwd / "preview.png").write_bytes(b"png")
        else:
            (cwd / "out.stl").write_text("vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 1\n")
        return subprocess.CompletedProcess(cmd, 0, "3D object (manifold)\nGenus: 0", "")

    monkeypatch.setattr(g.subprocess, "run", run)
    g.generate(M, {}, preview=True)
    assert len(calls) == 2


def test_public_runtime_has_no_model_source_steps():
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "Dockerfile").read_text()
    assert "git clone" not in runtime
    assert " /models" not in runtime
    assert "COPY --from" not in runtime


def test_unknown_model_rejected():
    from scad_mcp.server import generate
    with pytest.raises(ValueError):
        generate("nope", {})

@pytest.mark.integration
@pytest.mark.skipif(g.RENDERER != "local" and not shutil.which("docker"), reason="needs local renderer or docker + scad-proof image")
def test_render_end_to_end(monkeypatch):
    # repo-local dir: Docker Desktop doesn't share pytest's /private/var tmp
    tmp_path = Path(tempfile.mkdtemp(dir=Path(__file__).resolve().parents[1], prefix=".verify."))
    tmp_path.chmod(0o777)  # the image runs as UID 568
    try:
        monkeypatch.setattr(g, "ARTIFACTS", tmp_path)
        r = g.generate(M, {}, preview=True)
        assert (tmp_path / r["artifact"]).exists()
        assert r["bbox_mm"] == [41.49, 41.5, 52.74]
        assert r["manifold"] and r["genus"] == 0
        png = (tmp_path / r["preview"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(png[16:20], "big") == 800
        assert int.from_bytes(png[20:24], "big") == 600
        assert not list(tmp_path.glob(".work.*"))
    finally:
        shutil.rmtree(tmp_path)
