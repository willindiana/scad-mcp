# scad-mcp

Slicer- and printer-agnostic parametric model generator over MCP. No printer control. Models are JSON manifests with pinned upstream commits, parameter schemas and licenses; source code is fetched only by a separate, local-only model builder.

## Source-only v0.1.0

Server code is MIT, approved by owner. First release distributes source only: no wheel, model sources, binaries, container images or GHCR publication. Dockerfiles are recipes for local builds, not distributed images. Container publication remains blocked by security/source-compliance work in REDISTRIBUTION.md.

## Install and test

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/) and, for rendering, Docker with access to public upstream repositories. Extract source archive, enter its directory, then:

```sh
uv sync --locked
uv run --locked pytest -q -m 'not integration'
uv run python -c 'from scad_mcp.server import list_models; assert len(list_models()) == 3'
# Rendering: fetch pinned OpenSCAD image and model sources on YOUR machine.
# No private assets or published scad-mcp image needed.
./verify.sh
uv run --locked pytest -q
uv run scad-mcp
```

`./verify.sh` needs network during builds (base image, Debian/Python packages and public model clones), then runs proof renders. It pins OpenSCAD 2026.10.12 by digest and model commits; older distribution OpenSCAD 2021.01 is unsupported. Builds consume several GB; allow at least 10 GB free. Fetches remain local; do not publish resulting images/cache. Source-only tests and model listing need no OpenSCAD/models. Render tests carry `integration` marker. The dependency environment is installed from source checkout/archive; standalone wheel distribution is not supported in v0.1.0.

`scad-mcp` defaults to stdio. Configure MCP client command `uv`, arguments `run --directory /path/to/scad-mcp scad-mcp`. Run from project directory so default `artifacts/` is predictable, or set `SCAD_ARTIFACTS_DIR` explicitly. Host mode invokes Docker image `scad-proof` with network disabled. Never publish that local model-containing image or its build cache.

## Runtime image (no model sources)

```sh
docker build -t scad-mcp-runtime .
docker build -f Dockerfile.models -t scad-proof .
# Export only on YOUR machine after reviewing upstream licenses.
mkdir -p local-models artifacts
docker run --rm --network none --user 0 -v "$PWD/local-models:/export" --entrypoint sh scad-proof -ec 'cp -a /models/. /export/'
```

Mount `local-models` read-only at `/models` in runtime container; mount artifacts read-write at `/artifacts`. Public runtime contains manifests only, not upstream model sources. It will not render without mounted models. `Dockerfile.models` fetches pinned models at build time and is deliberately separate from distributable `Dockerfile`. Do not push builder images or remote caches.

Runtime image runs UID 568, HTTP transport, port 8781, local renderer. Supply `SCAD_MCP_API_KEY_FILE` (default `/run/secrets/scad-mcp-api-key`) as owner-only regular file owned by UID 568, 32–4096 printable ASCII bytes, no whitespace. Send `Authorization: Bearer <key>`. Optional `SCAD_MCP_GATEWAY_KEY_FILE` accepts a second independently revocable key; equal/missing/unsafe keys fail startup. Both keys grant every tool. Use TLS through trusted proxy; never expose unauthenticated HTTP or give container Docker socket. Use read-only root filesystem, exec-capable `/tmp` tmpfs and only artifacts writable. Local rendering does not itself enforce network isolation; enforce runtime egress policy outside application. Set trusted hosts/origins explicitly for your deployment if using proxies.

`.env.example` documents optional settings; application reads environment variables, not `.env` automatically. Keep real secret files outside repository and model context. Copy neither `.env` nor secret files into image.

## Tools

- `list_models()`: manifests, parameter schemas, presets, resolved defaults and licenses.
- `generate(model_id, params={}, allow_unknown_license=false, preview=false, preset=null)`: validated STL, bbox, facet count, manifold status and genus; optional 800×600 PNG. Returns artifact filename relative to artifacts directory. Does not slice or print.

```python
generate("gridfinity_extended")  # standard 1×1×7 bin
generate("gridfinity_extended", params={"width": 4, "depth": 3, "height": 4})
generate("gridfinity_baseplate", params={"drawer_size": [420, 380], "alignment": [0, 0]})
generate("cable_raceway", params={"length": 100})
```

Unknown keys, type/range errors and unreviewed licenses fail before rendering. Values travel through customizer preset JSON (`-p preset.json -P p`), never `-D`. Manifest default < named preset < per-call parameters. Strings remain plain customizer JSON strings. Manifests are trusted code/configuration, not user uploads.

`SCAD_PRESETS_FILE` optionally points to read-only JSON: `{ "gridfinity_extended": { "presets": { "magnetic": { "enable_magnets": true } }, "default_preset": "magnetic" } }`. New presets inherit manifest parameter defaults, cannot replace shipped preset names, and validate at startup. `default_preset: null` disables preset selection.

## Models and licenses

Server code: MIT (owner approved). License applies only to this project, not upstream models, OpenSCAD or dependencies.

| Model | Upstream | License |
| --- | --- | --- |
| `gridfinity_extended` | [ostat/gridfinity_extended_openscad](https://github.com/ostat/gridfinity_extended_openscad) | GPL-3.0 |
| `cable_raceway` | [KayosMaker/ParametricCableRacewayAndLid](https://github.com/KayosMaker/ParametricCableRacewayAndLid) | GPL-3.0 |
| `gridfinity_baseplate` | [yawkat/GridFlock](https://github.com/yawkat/GridFlock) | MIT (upstream dual MIT/CC-BY-4.0) |

Pins live in manifests and `Dockerfile.models`. Adding a model requires license review, schema, pinned local builder fetch and tests. openGrid has no license and is not included; an unknown-license override is NOT redistribution permission. Review upstream terms before sharing source or generated geometry. Runtime invocation of separately obtained models does not relicense those models. OpenSCAD/base-image distribution obligations remain separate; review before publishing image.

## Limits

Render timeout 300 seconds; preview timeout 60 seconds. PNG is visual aid, not printability proof. STL metrics are not physical-safety approval. No quotas, job queue or per-client tool scopes: keep trusted-user-only, add external rate/resource limits for HTTP deployments. Artifacts persist; operator handles retention.

GridFlock defaults to thin skeletonized baseplate, incompatible with magnets/click latch; use `preset="standard"` for those. `drawer_size` is finished outer size in mm (allow clearance), `bed_size` defaults to 250×250, `alignment` ranges 0–1 (0 west/south, 1 east/north). Segments appear together with gaps: split into objects in slicer before arranging. Non-42-mm sizes may produce tiny seam slivers; inspect and remove them. GridFlock is not GRIPS-compatible. Cable raceway lid is not offered because it fails manifold checks. No arbitrary SCAD execution or unlicensed model redistribution supported.

See SECURITY.md, RELEASE_CHECKLIST.md and REDISTRIBUTION.md. GPL permits redistribution with conditions; model exclusion is project policy, not a GPL prohibition. Separate-model HTTP runtime remains a local development recipe, not approved deployment change. MIT and source-only v0.1.0 scope are approved; publishing staged content still requires separate final owner authorization. GHCR/image publication remains blocked.
