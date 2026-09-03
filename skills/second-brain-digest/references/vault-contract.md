# Evidence Intake Contract

## Public default layout

```text
<vault>/
├── .AGENTS.md                     Vault-specific authority and rules
├── inbox/                         Temporary, not-yet-admitted material
├── evidence/
│   ├── sources/<root-id>/...      Canonical Source bytes
│   ├── .intake/<run-id>/          Private plans and receipts
│   └── .processing/<batch-id>/    Private semantic-batch state
├── attachments/                   Derived presentations and rebuildable artifacts
└── <vault-specific core notes>    Canonical knowledge owned by the vault
```

The scripts require `.AGENTS.md` and the `evidence/` contract. Core-note directories are defined by the vault, not by this public Skill. Object, relationship, and event are semantic roles; they do not automatically require matching folders.

## Source and Evidence

- A `Source` is an admitted canonical byte stream under `evidence/sources/`.
- `Evidence` is a precise reference from a conclusion to a Source: Source ID, vault-relative path, SHA-256, and locator.
- OCR, transcription, parsed JSON, summaries, and previews are derived artifacts. They never replace the Source and must record how they can be rebuilt.
- Equal hashes can reveal duplicate bytes, but do not prove that two source contexts are interchangeable or authorize deletion.

## Planning and movement

1. Accept only explicitly listed Source roots. Reject `/`, the user's home directory, the vault root, and any ancestor or child that would overlap the target `evidence/` tree.
2. Do not follow symbolic links. Report links, devices, sockets, unreadable files, and scan-time drift as blocked.
3. `plan` records absolute origin paths privately, stable relative destinations, size, modification time, SHA-256, Source ID, exclusions, and a plan digest. It never moves files.
4. `apply` requires the exact plan digest and performs a full preflight before the first move. Any drift means zero moves.
5. On one filesystem, prefer atomic rename. Across filesystems, copy to a temporary target, fsync, verify the hash, atomically place it, and only then remove the origin.
6. Write and fsync a receipt after each completed item. Resume only when the target hash matches the plan.
7. Do not remove directories unless the user authorized `--prune-empty`; never remove the Source root itself.
8. Plans and receipts contain private absolute paths. Keep `evidence/.intake/`, `evidence/.processing/`, and confidential Sources outside public repositories.

Before moving Desktop, Documents, Downloads, cloud-sync folders, application data, or code repositories, present the exact top-level roots and exclusions. A broad instruction to organize files does not silently authorize breaking application references or deleting originals.
