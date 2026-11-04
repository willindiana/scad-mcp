import shutil
import tempfile
from pathlib import Path

import pytest

from scad_mcp import generate as g
from scad_mcp.registry import load_registry


CABLE = load_registry()["cable_raceway"]


def test_preset_and_rejected_lid():
    assert g.build_preset(CABLE, {"length": 100}) == {
        "rw_length": "100", "rw_width": "30", "rw_height": "20", "part": "raceway"
    }
    with pytest.raises(ValueError):
        g.build_preset(CABLE, {"part": "lid"})


@pytest.mark.integration
@pytest.mark.skipif(g.RENDERER != "local" and not shutil.which("docker"), reason="needs local renderer or docker + scad-proof image")
def test_render(monkeypatch):
    tmp = Path(tempfile.mkdtemp(dir=Path(__file__).resolve().parents[1], prefix=".verify."))
    tmp.chmod(0o777)  # the image runs as UID 568
    try:
        monkeypatch.setattr(g, "ARTIFACTS", tmp)
        cable = g.generate(CABLE, {"length": 100})
        assert (tmp / cable["artifact"]).exists()
        assert cable["bbox_mm"] == [30.0, 100.0, 18.8]
        assert cable["manifold"] and cable["genus"] == 0
    finally:
        shutil.rmtree(tmp)
