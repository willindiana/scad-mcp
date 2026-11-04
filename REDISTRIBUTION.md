# Redistribution review — source-only v0.1.0

Owner approved MIT in LICENSE for server code and source-only first release scope. Final publication authorization remains separate. No upstream model sources, binaries or container images are distributed with this source release. Referenced licenses are not relicensed under MIT; local builds fetch third-party content directly from upstream. No copied upstream source or license-text excerpts are included; model manifests contain references and project-written parameter schemas. Third-party license links below document those references.

Source-only distribution avoids redistribution of OpenSCAD/base-image binaries; it does not clear those images for later publication. Following container review is retained for future work, not a source-release blocker.

## Models: policy is not a GPL prohibition

GPL permits redistribution, including commercial redistribution, subject to its conditions. Excluding referenced model sources from public runtime is this project's chosen release policy, NOT a legal claim that GPL forbids bundling. A separately invoked OpenSCAD program does not by itself require licensing independent server code under GPL. Review derivative/combined-work questions separately; MIT is GPL-compatible.

Pinned upstream license files reviewed:

- gridfinity_extended, commit `94d5a3e2d39e0b90894c042a255fc487cfcc9197`: [GPL v3 text](https://github.com/ostat/gridfinity_extended_openscad/blob/94d5a3e2d39e0b90894c042a255fc487cfcc9197/LICENSE).
- cable_raceway, commit `fcbcee8d03d14bffe2067205c111a84aa0d4ad60`: [GPL v3 text](https://github.com/KayosMaker/ParametricCableRacewayAndLid/blob/fcbcee8d03d14bffe2067205c111a84aa0d4ad60/LICENSE.md).
- GridFlock, commit `033e8f9dab860ce7ef46ca3f1dd656a1d13c5310`: [MIT/CC-BY-4.0 dual license](https://github.com/yawkat/GridFlock/blob/033e8f9dab860ce7ef46ca3f1dd656a1d13c5310/LICENSE), but some `opengrid/` models explicitly CC-BY-4.0 only, with attribution to DavidD and mitufy. Do not describe every file in full clone as MIT. Local builder clones whole repository; public runtime contains none of it.
- openGrid-3D/openGrid-openSCAD: GitHub license endpoint returned 404; absence of recognized license is not exhaustive legal review. No redistribution permission established, so excluded. Different repository from GridFlock's licensed `opengrid/` files.

GPL model redistribution, if later approved, must retain license/copyright notices, provide preferred source form and applicable modification notices, and satisfy GPLv3 source/installation requirements when conveying covered object code. Generated geometry's status depends on incorporated copyrighted material and upstream terms, not merely use of OpenSCAD. No blanket claim that all output is GPL or unrestricted.

## OpenSCAD/base image: still covered even without model sources

Pinned base: `openscad/openscad:trixie.2026-10-12@sha256:4098a7c2c37d5a9110121635a568e6596b8619362ced5c84cc67f47d395e7fd0`. Runtime reports OpenSCAD 2026.10.12. Local inspected build is arm64; amd64 publication needs its own build and scan.

Official [OpenSCAD COPYING](https://github.com/openscad/openscad/blob/master/COPYING) contains GPLv2 and CGAL linking exception. [Current upstream Dockerfile](https://github.com/openscad/docker-openscad/blob/main/openscad/trixie/Dockerfile) labels image GPL-3.0-or-later. These observations are NOT proof of exact pinned binary's license election, source revision, patches, submodules or build inputs. Date-matching Git commit is not proof either. Resolve exact binary provenance with upstream or reproducible rebuild before distributing.

Publishing derived OCI image redistributes OpenSCAD, Debian packages, MCAD libraries, fonts, Python packages and other components in its layers. Pulling upstream image does not transfer publisher's compliance duties to upstream. GPL/LGPL are not license violations by themselves.

Before image release:

1. Identify exact corresponding source for OpenSCAD and linked covered components, including submodules, patches and scripts controlling compilation/installation. Retain required notices/license texts, including CGAL exception where applicable. Build evidence currently insufficient; no exact OpenSCAD source bundle/offer established.
2. Inventory each distributed package/version and applicable license. Debian `/usr/share/doc/*/copyright` and common licenses help, but do not themselves provide corresponding source. Acquire exact Debian source package versions and any patches/build scripts; preserve notices for permissive packages too. LGPL obligations may require relinking materials depending on linking/distribution form.
3. Choose compliant source delivery per actual license version. Preferred: accompany binary access with complete matching source access on same distribution site, or compliant clearly documented equivalent source access where license permits. GPLv2 §3(b) written offer must be valid at least three years and cover any third party; GPLv3 §6 has distinct options/terms. A general GitHub link or upstream's unverified offer is insufficient. Do not claim System Libraries exception excuses all packages shipped in image.
4. Review MCAD, fonts/examples and non-code assets individually; retain applicable notices/attributions. Scan license classification is inventory aid, not legal clearance.
5. Scan exact final architecture-specific image and release source archive. Current image has unresolved HIGH/CRITICAL vulnerability findings; do not publish it.

Official guidance: [GPLv2 §3](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html#section3), [GPLv3 §6](https://www.gnu.org/licenses/gpl-3.0.html#section6), [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html). Compliance plan and license decisions remain owner-review gates.

## Deployment compatibility

Separate `Dockerfile.models` and read-only `/models` mount are provisional release-prep changes enforcing existing no-bundling policy. Existing private image remains unchanged; no deployment changed. Public runtime alone cannot render. Local `./verify.sh` builds model-containing proof image for tests; never publish it or its cache. Owner must approve this explicit installation contract before public release. Alternative is source-only initial release while container compliance/security work remains blocked; publishing bundled models requires separate policy decision, not GPL impossibility.
