import shutil
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from scad_mcp import generate as g
from scad_mcp.registry import Param, load_registry

BASE = load_registry()["gridfinity_baseplate"]

THIN = {
    "plate_size": "[210, 210]",
    "bed_size": "[250, 250]",
    "alignment": "[0.5, 0.5]",
    "hollow": "true",
    "hollow_wall": "0.8",
    "magnets": "false",
    "click": "false",
    "connector_intersection_puzzle": "true",
    "intersection_puzzle_fit": "1",
    "numbering": "true",
    "remove_bottom_lip": "true",
}


def test_thin_is_the_default_and_keeps_a_drawer_sized_override():
    assert g.build_preset(BASE, {}) == THIN
    assert g.build_preset(BASE, {"drawer_size": [420, 380]}) == {
        **THIN, "plate_size": "[420, 380]"
    }


def test_standard_preset_is_solid_and_can_use_magnets():
    standard = g.build_preset(BASE, {}, preset="standard")
    assert standard["hollow"] == "false"
    assert standard["remove_bottom_lip"] == "false"
    assert g.build_preset(BASE, {"enable_magnets": True}, preset="standard")["magnets"] == "true"


def test_alignment_can_put_leftover_padding_on_one_side():
    p = g.build_preset(BASE, {"drawer_size": [548, 88], "alignment": [0, 0]})
    assert p["plate_size"] == "[548, 88]"
    assert p["alignment"] == "[0, 0]"


def test_alignment_rejects_values_outside_the_grid():
    with pytest.raises(ValueError):
        g.build_preset(BASE, {"alignment": [0.5, 1.1]})


def test_vec2_maps_to_a_scad_array():
    p = Param(type="vec2", default=[1, 2], scad_name="v", scad_format="[{}, {}]")
    assert g._scad_value("v", p, [3.5, 4]) == "[3.5, 4]"


@pytest.mark.parametrize("bad", [
    [420],
    [420, 380, 1],
    ["420", 380],
    [420, True],
    [420, float("nan")],
    [41, 380],
    [420, 1001],
])
def test_bad_drawer_size_rejected(bad):
    with pytest.raises(ValueError):
        g.build_preset(BASE, {"drawer_size": bad})


@pytest.mark.parametrize("fmt", ["[{}]", "[{}, {}, {}]", "[{}, x]", "{{}}", "{}, {}"])
def test_vec2_format_needs_two_numeric_placeholders(fmt):
    with pytest.raises(ValidationError):
        Param.model_validate({
            "type": "vec2", "default": [1, 2], "scad_name": "v", "scad_format": fmt,
        })


def test_scalar_format_still_needs_one_placeholder():
    with pytest.raises(ValidationError):
        Param.model_validate({
            "type": "int", "default": 1, "scad_name": "v", "scad_format": "[{}, {}]",
        })


@pytest.mark.integration
@pytest.mark.skipif(g.RENDERER != "local" and not shutil.which("docker"), reason="needs local renderer or docker + scad-proof image")
def test_thin_plate_renders(monkeypatch):
    tmp = Path(tempfile.mkdtemp(dir=Path(__file__).resolve().parents[1], prefix=".verify."))
    tmp.chmod(0o777)  # the image runs as UID 568
    try:
        monkeypatch.setattr(g, "ARTIFACTS", tmp)
        plate = g.generate(BASE, {"drawer_size": [84, 84]})
        assert (tmp / plate["artifact"]).exists()
        assert plate["bbox_mm"] == [84.0, 84.0, 4.65]
        assert plate["facets"] == 4470
        assert plate["manifold"] and plate["genus"] == 9
    finally:
        shutil.rmtree(tmp)
