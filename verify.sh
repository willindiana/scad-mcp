#!/bin/sh
# Build pinned image, render proof bin, assert STL metrics. Exit non-zero on any drift.
set -eu
cd "$(dirname "$0")"
docker build -q -t scad-mcp-runtime . >/dev/null
# Local-only proof image; model sources must never enter a published image/cache.
docker build -q -f Dockerfile.models -t scad-proof . >/dev/null
out=$(mktemp -d "$PWD/.verify.XXXXXX")
chmod 777 "$out"  # the image runs as UID 568
trap 'rm -rf "$out"' EXIT
cp proof/preset.json proof/baseplate-preset.json "$out/"
docker run --rm -w /work -v "$out:/work" scad-proof \
  openscad --backend=Manifold -p preset.json -P proof -o out.stl \
  /models/gridfinity_extended/gridfinity_basic_cup.scad >"$out/log" 2>&1 || { cat "$out/log"; exit 1; }
python3 - "$out/out.stl" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
v = [tuple(map(float, m)) for m in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', t)]
n = len(v) // 3
bb = [round(max(c) - min(c), 2) for c in zip(*v)]
assert n == 9096, f"facets {n} != 9096"
assert bb == [167.49, 125.50, 31.74], f"bbox {bb}"
print("OK bin facets", n, "bbox", bb)
PY
grep -q "3D object (manifold)" "$out/log" && grep -qE "Genus: +0" "$out/log" || { echo "bin not manifold/genus 0"; exit 1; }
echo "OK bin manifold genus 0"
docker run --rm -w /work -v "$out:/work" scad-proof \
  openscad --backend=Manifold -p baseplate-preset.json -P proof -o baseplate.stl \
  /models/gridfinity_baseplate/gridflock.scad >"$out/baseplate.log" 2>&1 || { cat "$out/baseplate.log"; exit 1; }
python3 - "$out/baseplate.stl" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
v = [tuple(map(float, m)) for m in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', t)]
n = len(v) // 3
bb = [round(max(c) - min(c), 2) for c in zip(*v)]
assert n == 4470, f"baseplate facets {n} != 4470"
assert bb == [84.0, 84.0, 4.65], f"baseplate bbox {bb}"
print("OK baseplate facets", n, "bbox", bb)
PY
grep -q "3D object (manifold)" "$out/baseplate.log" && grep -qE "Genus: +9" "$out/baseplate.log" || { echo "baseplate not manifold/genus 9"; exit 1; }
echo "OK baseplate manifold genus 9"
