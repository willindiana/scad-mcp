"""Manifest-driven model registry. Models are JSON data files; no per-model code."""
import json
import math
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown manifest keys are errors


class Param(_Strict):
    type: Literal["int", "number", "bool", "enum", "vec2"]
    description: str = ""
    default: int | float | bool | str | list[float]
    min: float | None = None
    max: float | None = None
    values: list[str] | None = None
    scad_name: str  # customizer variable name
    scad_format: str = "{}"  # one placeholder for scalars, two for vec2

    def _check_number(self, v) -> None:
        if type(v) is bool or not isinstance(v, int | float):
            raise ValueError(f"expected {self.type}")
        if self.type == "int" and not isinstance(v, int):
            raise ValueError("expected int")
        if not math.isfinite(v):
            raise ValueError("not finite")
        if self.min is not None and v < self.min or self.max is not None and v > self.max:
            raise ValueError(f"must be in [{self.min}, {self.max}]")

    def check_value(self, v) -> None:
        """Reject a value that is the wrong type or outside this param's range."""
        if self.type == "bool":
            if type(v) is not bool:
                raise ValueError("expected bool")
            return
        if self.type == "enum":
            if type(v) is not str or v not in self.values:
                raise ValueError(f"must be one of {self.values}")
            return
        if self.type == "vec2":
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("expected [x, y]")
            for n in v:
                self._check_number(n)
            return
        self._check_number(v)

    @model_validator(mode="after")
    def _check(self):
        placeholders = 2 if self.type == "vec2" else 1
        remaining = self.scad_format.replace("{}", "")
        if self.scad_format.count("{}") != placeholders or not re.fullmatch(r"[\[\], 0-9.]*", remaining):
            raise ValueError(
                f"scad_format must contain exactly {placeholders} {{}} placeholder(s) with numeric array syntax only"
            )
        if self.type == "vec2" and not (self.scad_format.startswith("[") and self.scad_format.endswith("]")):
            raise ValueError("vec2 scad_format must be a bracketed array")
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", self.scad_name):
            raise ValueError("scad_name must be an OpenSCAD identifier")
        if (self.type == "enum") != bool(self.values):
            raise ValueError("values required for enum, forbidden otherwise")
        if self.type == "enum" and self.default not in self.values:
            raise ValueError("default not in values")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        self.check_value(self.default)
        return self


class Upstream(_Strict):
    repo: str = Field(pattern=r"^https://")
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")  # full SHA, never a branch/tag


class Manifest(_Strict):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    description: str = ""
    upstream: Upstream
    license: str | None = None
    entry: str = Field(pattern=r"^[\w./ -]+\.scad$")
    params: dict[str, Param]
    presets: dict[str, dict[str, Any]] = {}
    default_preset: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if ".." in self.entry.split("/") or self.entry.startswith("/"):
            raise ValueError("entry must be a relative path inside the repo")
        for k in self.params:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", k):
                raise ValueError(f"bad param name {k!r}")
        for name, values in self.presets.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                raise ValueError(f"bad preset name {name!r}")
            unknown = set(values) - set(self.params)
            if unknown:
                raise ValueError(f"preset {name!r}: unknown params {sorted(unknown)}")
            for k, v in values.items():
                try:
                    self.params[k].check_value(v)
                except ValueError as e:
                    raise ValueError(f"preset {name!r}: {k}: {e}") from e
        if self.default_preset is not None and self.default_preset not in self.presets:
            raise ValueError(f"default_preset {self.default_preset!r} is not a declared preset")
        return self


def load_registry(directory: Path = MODELS_DIR) -> dict[str, Manifest]:
    reg: dict[str, Manifest] = {}
    for f in sorted(directory.glob("*.json")):
        m = Manifest.model_validate(json.loads(f.read_text()))
        if m.id != f.stem:
            raise ValueError(f"{f.name}: id {m.id!r} must match filename")
        reg[m.id] = m
    return reg


def merge_user_presets(reg: dict[str, Manifest], path: Path) -> dict[str, Manifest]:
    """Merge additive per-install presets from a JSON file into a loaded registry.

    User presets cannot replace shipped preset names, so calls that reference
    `standard` (or any shipped preset) keep the same meaning on every install.
    """
    path = Path(path)
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError(f"{path}: presets file must be under 1 MiB")
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object keyed by model id")
    out = dict(reg)
    for model_id, override in data.items():
        if model_id not in reg:
            raise ValueError(f"{path}: unknown model {model_id!r}")
        if not isinstance(override, dict):
            raise ValueError(f"{path}: {model_id}: must be an object")
        unknown = set(override) - {"presets", "default_preset"}
        if unknown:
            raise ValueError(f"{path}: {model_id}: unknown keys {sorted(unknown)}")
        presets = override.get("presets", {})
        if not isinstance(presets, dict):
            raise ValueError(f"{path}: {model_id}: presets must be an object")
        clash = set(presets) & set(reg[model_id].presets)
        if clash:
            raise ValueError(f"{path}: {model_id}: cannot replace shipped presets {sorted(clash)}; use a new name")
        m = reg[model_id]
        out[model_id] = Manifest.model_validate({
            **m.model_dump(),
            "presets": {**m.presets, **presets},
            "default_preset": override.get("default_preset", m.default_preset),
        })
    return out
