# Source-backed Knowledge Evolution Protocol

## Goal

Turn one complete, bounded Source batch into the minimum necessary updates to an existing knowledge vault. The result should make the current object, event, state, basis, conflict, and unknown understandable without turning every source fragment into a new note.

## Required input

Each semantic batch needs:

1. admitted Source IDs, hashes, vault-relative paths, and stable locators;
2. complete ordered content or a verified derived representation;
3. the full current text and SHA-256 of every note that may change;
4. the vault's concept, role, relationship, and lifecycle constraints;
5. `digest-result.schema.json`.

Without the current notes, the model may propose candidates but cannot claim duplicate convergence or a correct update-versus-create decision.

## Reasoning order

1. Understand the Source purpose, participants, time, events, state changes, contradictions, missing attachments, and unresolved references.
2. Resolve identity before structure. Similar names do not prove one object; aliases need stable supporting evidence.
3. Ask whether durable state changed. Repetition, greetings, restatement, or already represented information becomes `no_change`.
4. Update current state instead of appending an endless log. Preserve earlier state through the existing timeline or version history.
5. Use an event for a change that can answer what happened, when, to whom, and with what result. Do not compress an entire project into one ever-growing event.
6. Prove relationships independently. Co-occurrence is not a relationship.
7. Keep conflicting claims together and keep unknowns unknown. A filename or missing attachment is not enough to infer contents.
8. Treat a repeatable decision method as a candidate until its trigger, rule, output, scope, counterexamples, validation state, and Evidence are clear.
9. Treat person-level beliefs or values as optional, revisable candidates only when the user needs them for a bounded decision. Distinguish direct statements from inference, record confidence and counterevidence, and avoid unrelated private details.

## Candidate extraction and authority

Parallel readers may process non-overlapping Sources or ordered windows only when the user authorizes parallel work. They output candidates and locators, never edits to canonical notes. One aggregator rereads overlapping identities and methods, resolves duplicates and ordering, and creates one final `result.json`. Canonical writes remain serial.

## Applying note changes

- Prefer one existing canonical note for each stable object.
- Put events in an object's or project's existing timeline unless an event needs independent ownership, status, or long-term reference.
- Do not create one file per atomic statement.
- Reuse the vault's approved relationship types. Put unapproved nuance in explanation or unknowns.
- The model proposes an ordered result; the acting agent rereads and edits each current file. Read-set drift requires a fresh decision.

## Evidence contract

Every changed state, event, relationship, claim, method candidate, conflict, or exception must include:

```text
source_id + evidence/sources/... path + sha256 + locator
```

Use stable format locators: page, heading or paragraph, sheet and cell, message ID and timestamp, media time range, or text line. A short excerpt may help review but never replaces the locator.

## Duplicate convergence

1. Search names, headings, aliases, stable external identity, definitions, and current state.
2. If identity or definition is the same, choose one current authority and move valid aliases or content there.
3. If boundaries differ, keep both only when each needs separate ownership and lifecycle.
4. If identity cannot be proved, do not merge or delete. Return `decision_required` with evidence and impact.
5. Redirect or remove old entries only after explicit deletion authority and link readback.

One batch produces one ordered schema-valid result. It does not edit Source bytes or bypass the current-note read set.
