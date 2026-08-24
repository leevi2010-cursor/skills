# Repository Guidance

This repository is the public distribution source for the portable Skills registered in `portable-skill-registry.json`.

- Keep one Skill in `skills/<skill-name>/`; every Skill must contain `SKILL.md` with valid `name` and `description` frontmatter.
- Keep registry `source` paths relative to the repository root and installation targets under the intended runtime's Skill directory.
- Treat installed copies such as `~/.codex/skills/` as projections, never as sources to copy back without an explicit reconciliation.
- Preserve each Skill's supporting `agents/`, `scripts/`, `references/`, and `assets/` files when they are referenced by `SKILL.md`.
- Before publishing, run the Skill Creator validator, exercise changed scripts with deterministic fixtures, run the portable manager check, scan for credentials and private data, and inspect the staged diff.
- Never commit API keys, credentials, private business documents, personal data, generated user content, local caches, or machine-specific absolute paths.
- Keep README installation commands aligned with the registry and manager behavior.
