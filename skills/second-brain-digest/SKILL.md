---
name: second-brain-digest
description: Admit authorized local files into a governed Second Brain vault and consolidate them into the minimum source-backed objects, relationships, events, timelines, and current state. Use for evidence intake, knowledge digestion, duplicate-note convergence, or updating existing vault knowledge without blind append.
---

# Second Brain Digest

Turn bounded local material into traceable Sources and minimal, evolving knowledge. The public Skill contains workflow code and generic contracts only; each user's vault rules, authority structure, content, and project configuration remain private and authoritative.

## Configuration and authority

Set the vault root explicitly for each shell session:

```bash
SECOND_BRAIN_ROOT="/path/to/knowledge-vault"
```

The vault must contain a root `.AGENTS.md`. Read it before any inventory, move, or knowledge update. Use the core-note directories and concept registry named there; do not assume another user's `Projects/`, `people/`, `Methods/`, or governance layout.

The scripts use these public defaults below the configured vault root:

- `evidence/sources/`: admitted canonical Source bytes.
- `evidence/.intake/`: private intake plans and receipts.
- `evidence/.processing/`: private semantic-batch state.

The vault owner must keep `.intake/`, `.processing/`, and confidential Source bytes out of public Git history. Installed Skill copies are runtime projections, not knowledge authority.

## Read the matching contract

- For inventory or file admission, read [the vault intake contract](references/vault-contract.md).
- For semantic digestion, note updates, or convergence, read [the knowledge evolution protocol](references/digest-protocol.md) and use [the result schema](references/digest-result.schema.json).
- For PDF, office files, images, audio, video, or chat exports, read [the format adapter contract](references/format-adapters.md).

## Workflow

1. **Bound the request.** Identify exact Source roots, exclusions, requested mode, authority owner, and whether moving files is authorized. Inventory permission alone does not authorize a move or note edit.
2. **Inventory.** Read metadata and only the hashes needed for a deterministic plan. Do not follow symbolic links or scan broad roots such as `/`, the home directory, or the vault itself.
3. **Plan admission.** Run `evidence_intake.py plan`. Review the plan summary, exclusions, blocked paths, total files, total bytes, and `plan_digest`. Planning never moves a file.
4. **Apply only the approved plan.** Run `apply` only when the user has authorized that exact scope. Pass the exact digest to `--confirm`; preflight failure must result in zero moves.
5. **Fix the semantic batch.** Read the complete Source batch and every existing note that may be updated. Run `digest_batch.py prepare` with stable Source IDs and the vault-relative read set.
6. **Prefer update over append.** Resolve stable identity, current state, events, relationships, conflicts, and unknowns. Update a canonical note when it can absorb the information. Create a candidate only when the vault needs an independently owned, repeatedly referenced object or method.
7. **Produce one ordered result.** Save one `result.json` under the prepared batch. Parallel readers may emit candidates only when the user authorizes parallel work; one aggregator resolves duplicates and ordering before the final result.
8. **Validate before editing.** Run `digest_batch.py validate`. Evidence references must match admitted Source ID, vault-relative path, SHA-256, and a stable locator. If the Source or read set drifted, reread instead of overwriting.
9. **Apply serially and complete.** Edit only the validated notes, then run `complete` with every changed or newly created note. Read back Source hashes, note hashes, conflicts, and residue before reporting completion.

## Evidence and privacy rules

Each changed state, event, relationship, claim, or conflict needs at least:

```text
source_id + vault-relative source path + sha256 + locator
```

Keep credentials, identifiers, addresses, private conversations, health details, and unrelated personal information in the private Source layer unless the user has authorized a specific long-term business use. Store only the minimum fields needed for the decision. Missing content stays unknown; filenames and placeholders are not evidence of contents.

Do not convert a repeated mention into a new object, co-occurrence into a relationship, one case into a universal method, or a model inference into a permanent fact. Preserve competing claims when identity or authority cannot be proved.

## Commands

Create a no-move intake plan:

```bash
python3 scripts/evidence_intake.py plan \
  --vault "$SECOND_BRAIN_ROOT" \
  --source "/path/to/bounded-source" \
  --exclude-extension .dmg
```

Apply and verify one authorized plan:

```bash
python3 scripts/evidence_intake.py apply \
  --plan "$SECOND_BRAIN_ROOT/evidence/.intake/<run-id>/plan.json" \
  --confirm "<plan-digest>"

python3 scripts/evidence_intake.py status \
  --plan "$SECOND_BRAIN_ROOT/evidence/.intake/<run-id>/plan.json"
```

Prepare, validate, and complete a semantic batch:

```bash
python3 scripts/digest_batch.py prepare \
  --vault "$SECOND_BRAIN_ROOT" \
  --batch-id "digest_<stable-id>" \
  --source-id "src_<24-hex>" \
  --read-note "path/to/current-note.md"

python3 scripts/digest_batch.py validate \
  --vault "$SECOND_BRAIN_ROOT" \
  --batch-id "digest_<stable-id>"

python3 scripts/digest_batch.py complete \
  --vault "$SECOND_BRAIN_ROOT" \
  --batch-id "digest_<stable-id>" \
  --changed-note "path/to/current-note.md"
```

Index a long WeChat-style Markdown export without copying its message body:

```bash
python3 scripts/wechat_windows.py index \
  --source "$SECOND_BRAIN_ROOT/evidence/sources/<source-root>/<snapshot>.md" \
  --max-messages 1000
```

## Modes and stopping points

- `inventory`: report the bounded scope; do not move files or edit notes.
- `admit`: complete an authorized evidence intake and stop before semantic digestion.
- `digest`: update minimum knowledge from already admitted Sources; do not admit extra files.
- `consolidate`: compare duplicate notes and propose one authority; stop when identity, ownership, or deletion authority is unclear.
- `report`: summarize existing notes and receipts without creating a second fact store.

Stop the affected scope on incomplete reads, permission errors, Source drift, broken locators, conflicting identity, or missing authority. Preserve the Source, plan, batch result, and unknowns; never fill gaps by guessing.
