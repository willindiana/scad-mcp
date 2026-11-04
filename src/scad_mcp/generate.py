"""Validate params against a manifest, render via OpenSCAD customizer preset (-p/-P, never -D)."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .registry import Manifest, Param

ARTIFACTS = Path(os.environ.get("SCAD_ARTIFACTS_DIR", "artifacts")).resolve()
IMAGE = os.environ.get("SCAD_DOCKER_IMAGE", "scad-proof")  # built from ./Dockerfile
RENDERER = os.environ.get("SCAD_RENDERER", "docker")  # docker: host dev; local: inside service container
MODELS_ROOT = "/models"  # separately built model volume, mounted read-only
TIMEOUT = 300
PREVIEW_TIMEOUT = 60
KNOWN_LICENSES = {"GPL-3.0", "MIT"}  # ponytail: reviewed licenses only; expand after reviewing each new model

def _scad_value(name: str, p: Param, v):
    """Return a validated value's SCAD literal, or raise ValueError."""
    try:
        p.check_value(v)
    except ValueError as e:
        raise ValueError(f"{name}: {e}") from e
    if p.type == "bool":
        values = ["true" if v else "false"]
    elif p.type == "enum":
        values = [v]  # customizer JSON quotes strings; SCAD quotes here become part of the value
    elif p.type == "vec2":
        values = [f"{n:.10g}" for n in v]
    else:
        values = [str(v) if p.type == "int" else f"{v:.10g}"]
    parts = p.scad_format.split("{}")
    if len(parts) != len(values) + 1:
        raise ValueError(f"{name}: scad_format placeholder mismatch")
    return "".join(part + value for part, value in zip(parts, values)) + parts[-1]

def resolve_params(m: Manifest, params: dict, preset: str | None = None) -> dict:
    """Merge manifest defaults < preset values < per-call params."""
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    name = m.default_preset if preset is None else preset
    if name is not None and name not in m.presets:
        raise ValueError(f"unknown preset {name!r}; available: {sorted(m.presets)}")
    unknown = set(params) - set(m.params)
    if unknown:
        raise ValueError(f"unknown params: {sorted(unknown)}")
    merged = {**m.presets.get(name, {}), **params} if name is not None else dict(params)
    return {k: merged.get(k, p.default) for k, p in m.params.items()}

def build_preset(m: Manifest, params: dict, preset: str | None = None) -> dict[str, str]:
    resolved = resolve_params(m, params, preset)
    return {p.scad_name: _scad_value(k, p, resolved[k]) for k, p in m.params.items()}

def _run_cmd(scad: list[str], work: Path, init: bool = False) -> list[str]:
    """Host dev runs the pinned renderer image; the service container renders in place."""
    if RENDERER == "local":
        return scad
    if RENDERER != "docker":
        raise ValueError(f"SCAD_RENDERER must be 'docker' or 'local', not {RENDERER!r}")
    # xvfb-run needs a reaping init; the plain render path does not.
    extra = ["--init"] if init else []
    # Host-dev work dirs are owned by the invoking user; the throwaway renderer runs as root.
    return ["docker", "run", "--rm", *extra, "--user", "0:0", "--network", "none",
            "-w", "/work", "-v", f"{work}:/work", IMAGE, *scad]


def stl_metrics(path: Path, log: str) -> dict:
    t = path.read_text()
    v = [tuple(map(float, x)) for x in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", t)]
    genus = re.search(r"Genus:\s+(-?\d+)", log)
    return {
        "facets": len(v) // 3,
        "bbox_mm": [round(max(c) - min(c), 2) for c in zip(*v)] if v else [],
        "manifold": "3D object (manifold)" in log,
        "genus": int(genus.group(1)) if genus else None,
    }

def generate(m: Manifest, params: dict, allow_unknown_license: bool = False, preview: bool = False,
             preset: str | None = None) -> dict:
    if m.license not in KNOWN_LICENSES and allow_unknown_license is not True:
        raise ValueError(f"{m.id}: unknown or missing license {m.license!r}; pass allow_unknown_license=True to override")
    scad_params = build_preset(m, params, preset)  # raises before anything runs
    key = hashlib.sha256(json.dumps([m.id, m.upstream.commit, scad_params], sort_keys=True).encode()).hexdigest()[:12]
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=ARTIFACTS, prefix=".work."))  # under artifacts so Docker can mount it
    try:
        (work / "preset.json").write_text(json.dumps({"fileFormatVersion": "1", "parameterSets": {"p": scad_params}}))
        scad = ["openscad", "--backend=Manifold", "-p", "preset.json", "-P", "p", "-o", "out.stl",
                f"{MODELS_ROOT}/{m.id}/{m.entry}"]
        try:
            r = subprocess.run(_run_cmd(scad, work), cwd=work, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"render timed out after {TIMEOUT}s")
        log = r.stdout + r.stderr
        if r.returncode or not (work / "out.stl").exists():
            raise RuntimeError(f"openscad failed ({r.returncode}):\n{log[-2000:]}")
        metrics = stl_metrics(work / "out.stl", log)
        if not metrics["facets"] or not metrics["manifold"]:
            raise RuntimeError("openscad produced no valid manifold STL")
        name = f"{m.id}-{key}.stl"
        if preview:
            png = ["xvfb-run", "-a", "openscad", "--backend=Manifold", "-p", "preset.json", "-P", "p",
                   "--imgsize=800,600", "--autocenter", "--viewall", "-o", "preview.png",
                   f"{MODELS_ROOT}/{m.id}/{m.entry}"]
            try:
                r = subprocess.run(_run_cmd(png, work, init=True), cwd=work, capture_output=True, text=True, timeout=PREVIEW_TIMEOUT)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"preview timed out after {PREVIEW_TIMEOUT}s")
            if r.returncode or not (work / "preview.png").is_file() or (work / "preview.png").stat().st_size == 0:
                raise RuntimeError(f"preview failed ({r.returncode}):\n{(r.stdout + r.stderr)[-2000:]}")
        (work / "out.stl").replace(ARTIFACTS / name)
        result = {"artifact": name, "params": scad_params, **metrics}
        if preview:
            png_name = f"{m.id}-{key}.png"
            (work / "preview.png").replace(ARTIFACTS / png_name)
            result["preview"] = png_name
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)
