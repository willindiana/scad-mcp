import json

import pytest

from scad_mcp import generate as g
from scad_mcp.registry import load_registry, merge_user_presets

MODEL = "gridfinity_extended"


def merged(tmp_path, data):
    path = tmp_path / "presets.json"
    path.write_text(json.dumps(data))
    return merge_user_presets(load_registry(), path)


def test_additive_preset_is_usable(tmp_path):
    reg = merged(tmp_path, {
        MODEL: {"presets": {"magnetic": {
            "width": 1, "depth": 1, "height": 7,
            "enable_magnets": True, "label_style": "normal",
        }}}
    })
    m = reg[MODEL]
    assert set(m.presets) == {"standard", "magnetic"}
    assert g.resolve_params(m, {}, preset="magnetic")["enable_magnets"] is True
    assert g.build_preset(m, {}, preset="magnetic") == {
        "width": "[1, 0]", "depth": "[1, 0]", "height": "[7, 0]",
        "lip_style": "normal", "wall_thickness": "0",
        "enable_magnets": "true", "enable_screws": "false",
        "fingerslide": "none", "label_style": "normal",
    }


def test_user_can_change_their_default_preset(tmp_path):
    reg = merged(tmp_path, {
        MODEL: {
            "presets": {"tall": {"height": 10, "label_style": "normal"}},
            "default_preset": "tall",
        }
    })
    m = reg[MODEL]
    assert g.resolve_params(m, {})["height"] == 10
    assert g.resolve_params(m, {"height": 4})["height"] == 4


def test_null_default_preset_opts_out(tmp_path):
    reg = merged(tmp_path, {MODEL: {"default_preset": None}})
    assert g.resolve_params(reg[MODEL], {})["height"] == 3


def test_user_preset_can_capture_a_drawer_size(tmp_path):
    reg = merged(tmp_path, {
        "gridfinity_baseplate": {"presets": {"desk_drawer": {"drawer_size": [420, 380]}}}
    })
    m = reg["gridfinity_baseplate"]
    assert g.build_preset(m, {}, preset="desk_drawer")["plate_size"] == "[420, 380]"


def test_null_default_preset_falls_back_to_a_solid_baseplate(tmp_path):
    reg = merged(tmp_path, {"gridfinity_baseplate": {"default_preset": None}})
    m = reg["gridfinity_baseplate"]
    assert g.resolve_params(m, {})["hollow"] is False
    assert g.resolve_params(m, {})["remove_bottom_lip"] is False


@pytest.mark.parametrize("data,message", [
    ({MODEL: {"presets": {"standard": {"height": 9}}}}, "cannot replace shipped presets"),
    ({"nope": {"presets": {}}}, "unknown model"),
    ({MODEL: {"presets": {"x": {"bogus": 1}}}}, "unknown params"),
    ({MODEL: {"presets": {"x": {"width": 0}}}}, "preset 'x'"),
    ({MODEL: {"presets": {"x": {"label_style": "nope"}}}}, "preset 'x'"),
    ({MODEL: {"presets": {"x": {}}, "bogus": 1}}, "unknown keys"),
    ({MODEL: {"default_preset": "missing"}}, "not a declared preset"),
    ({MODEL: {"presets": []}}, "presets must be an object"),
])
def test_bad_user_presets_rejected(tmp_path, data, message):
    with pytest.raises((ValueError, TypeError), match=message):
        merged(tmp_path, data)
