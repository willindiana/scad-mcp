import json
import re
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from scad_mcp.registry import MODELS_DIR, load_registry

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_manifests_load_and_match_local_builder_pin():
    reg = load_registry()
    assert "gridfinity_extended" in reg
    assert "cable_raceway" in reg
    assert "gridfinity_baseplate" in reg
    dockerfile = (ROOT / "Dockerfile.models").read_text()
    for model, arg in (
        ("gridfinity_extended", "MODEL_COMMIT"),
        ("cable_raceway", "CABLE_RACEWAY_COMMIT"),
        ("gridfinity_baseplate", "GRIDFLOCK_COMMIT"),
    ):
        pin = re.search(rf"ARG {arg}=(\w+)", dockerfile).group(1)
        assert reg[model].upstream.commit == pin
        assert f"/models/{model} checkout --quiet \"${arg}\"" in dockerfile


def _write(d, name, **over):
    m = json.loads((MODELS_DIR / "gridfinity_extended.json").read_text())
    m.update(over)
    (d / f"{name}.json").write_text(json.dumps(m))


@pytest.mark.parametrize("over", [
    {"bogus": 1},                                            # unknown key
    {"upstream": {"repo": "https://x", "commit": "main"}},   # unpinned
    {"entry": "../../etc/passwd.scad"},                      # traversal
    {"id": "other"},                                         # id != filename
    {"presets": {"standard": {"bogus": 1}}},                 # unknown preset param
    {"presets": {"standard": {"width": 0}}},                 # preset value out of range
    {"presets": {"standard": {"width": 1.5}}},               # preset float for int
    {"presets": {"standard": {"width": "4); cube(1e9"}}},    # preset injection attempt
    {"presets": {"standard": {"label_style": "nope"}}},      # preset enum not in values
    {"presets": {"Bad Name": {}}},                           # bad preset name
    {"default_preset": "missing"},                           # default must exist
])
def test_bad_manifest_rejected(over):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        _write(d, "gridfinity_extended", **over)
        with pytest.raises((ValidationError, ValueError)):
            load_registry(d)
