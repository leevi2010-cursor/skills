# Repository Guidance

This repository is the distribution source for the portable Skills and read-only work documents registered in `portable-skill-registry.json`. Start with `README.md`; it separates shared expression principles, situational work methods, and optional Skills. Read the expression principles before writing user-facing material, and the decision loop when the task involves a decision or review, within their stated scope. This file governs work on this repository; it does not overwrite a user's global or project instructions.

- Keep one Skill in `skills/<skill-name>/`; every Skill must contain `SKILL.md` with valid `name` and `description` frontmatter.
- Keep registry `source` paths relative to the repository root and installation targets under the intended runtime's Skill directory.
- Treat installed copies such as `~/.codex/skills/` as projections, never as sources to copy back without an explicit reconciliation.
- Preserve each Skill's supporting `agents/`, `scripts/`, `references/`, and `assets/` files when they are referenced by `SKILL.md`.
- Before publishing, run the Skill Creator validator, exercise changed scripts with deterministic fixtures, run the portable manager check, scan for credentials and private data, and inspect the staged diff.
- Never commit API keys, credentials, private business documents, personal data, generated user content, local caches, or machine-specific absolute paths.
- Keep README installation commands aligned with the registry and manager behavior.
- Use the existing registry as the single catalog. Regenerate its README projection with `python3 scripts/render_catalog.py --write`, then run `--check`; do not maintain a second independent list. Keep document versions aligned with their headings; use content SHA-256 for Skills without a declared version.
- Keep `docs/work-methods/` as documents. The Skill manager must not install them or rewrite global `AGENTS.md`; use the existing sync prompt for a bounded, backed-up rules merge.
- Honor `CODEX_HOME` and preserve local Skill edits. Unknown drift requires comparison and explicit `--replace-local`; safety checks and backups still apply. Tests use temporary directories and fake tools, never real runtime installs, private vaults, or external business writes.
- See `docs/maintenance.md` for release checks. A canceled publication stops remote writes until new authorization; a created commit alone is not a published branch update.
