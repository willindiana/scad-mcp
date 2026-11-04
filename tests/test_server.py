from scad_mcp.server import list_models


def test_list_models():
    models = {m["id"]: m for m in list_models()}
    assert "gridfinity_extended" in models
    gridfinity = models["gridfinity_extended"]
    assert gridfinity["default_preset"] == "standard"
    assert "standard" in gridfinity["presets"]
    assert gridfinity["defaults"] == {
        "width": 1, "depth": 1, "height": 7,
        "lip_style": "normal", "wall_thickness": 0,
        "enable_magnets": False, "enable_screws": False,
        "fingerslide": "none", "label_style": "normal",
    }

    assert "gridfinity_baseplate" in models
    baseplate = models["gridfinity_baseplate"]
    assert baseplate["default_preset"] == "thin"
    assert {"thin", "standard"} <= set(baseplate["presets"])
    assert baseplate["defaults"]["drawer_size"] == [210, 210]
    assert baseplate["defaults"]["bed_size"] == [250, 250]
    assert baseplate["defaults"]["hollow"] is True
