# Release checklist

Evidence belongs in private project ticket, never raw matches. Unchecked gate means BLOCKED, not ready.

- [ ] Owner approves project license; dependency/model rights reviewed. No unlicensed models, copied private assets, or bundled GPL model sources in public image. Review base-image obligations separately.
- [ ] README covers install, auth, tools, limits, model licensing. LICENSE, SECURITY.md (GitHub private reports), CHANGELOG and non-1.0 semver present.
- [ ] Private defaults removed; `.env.example` contains no credentials or private paths/hosts. No personal email; public commits use verified GitHub noreply address.
- [ ] Tool trust boundaries validated; write/physical actions require explicit approval. Unknown parameters rejected, path traversal prevented, JSON presets used instead of code evaluation.
- [ ] Betterleaks full-history, commit metadata and working-tree scans pass generic AND private rules. Seeded test catches fake secret + personal path; clean repo passes.
- [ ] Tests and fresh-clone install smoke test pass; dependencies pinned; source archive and image scanned for secrets, vulnerabilities and licenses. Review findings, do not silently suppress.
- [ ] Pinned renderer build + integration test pass; inspect all image layers (deleting a source in later layer is insufficient). No model builder cache published.
- [ ] Forgejo checks green on exact staged commit; GitHub workflows pinned by SHA and permissions minimal.
- [ ] Owner reviews final staged tree and recorded evidence; verdict READY or BLOCKED with reasons.

## Fresh-history public mirror (owner approval required)

1. Keep original private repo and mirrors unchanged as archive. Create clean local export with `.git` omitted; initialize new history and one noreply-authored commit. Run full release gate again.
2. Owner approves final files, license and intended repository names. Only then create NEW public Forgejo repository and NEW public GitHub repository. Never flip old private repositories public.
3. Push fresh history to new Forgejo repository. Configure Forgejo push mirror to new GitHub repository with narrowly scoped credential stored only in Forgejo secrets. Verify branch/tag parity and no private refs.
4. Enable GitHub secret scanning, push protection and private vulnerability reporting. Protect main and tags; require review/checks. Create protected `public-release` environment with owner reviewer; restrict to release tags.
5. After owner approves first version and image review, create semver tag and mirror it. Manually dispatch GitHub release workflow at tag. Verify release and GHCR visibility/contents; publish no build caches or model-builder target. Record digest and rollback tag.
