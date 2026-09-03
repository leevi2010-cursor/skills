# Format Adapter Contract

## Purpose

Convert non-plain-text Sources into readable derived representations while preserving the original bytes and stable Evidence locators. Conversion answers how to read a Source; it does not decide object identity, relationships, events, or long-term state.

## Selection order

1. A currently installed, format-specific Skill or tool.
2. The format owner's official SDK or export tool.
3. A maintained, license-clear, version-pinnable open-source implementation.
4. Existing code already validated behind a bounded adapter.
5. Minimal custom parsing only when the earlier options cannot preserve the required structure or locator.

Before adding a parser, OCR model, transcription system, or conversion dependency, verify its current official documentation, license, supported platform, network behavior, model size, structured output, locator support, and damaged-input handling. Remote uploads or external APIs require explicit authorization for the Source involved.

## Adapter result

Record at least:

```json
{
  "source_id": "src_...",
  "source_sha256": "...",
  "adapter": "tool-or-library-name",
  "adapter_version": "pinned-version",
  "network_mode": "offline | authorized_remote",
  "derived_path": "evidence/.processing/<batch-id>/derived/...",
  "derived_sha256": "...",
  "locator_map": "page/paragraph/cell/timecode mapping",
  "quality": "verified | partial | failed",
  "limitations": []
}
```

Derived text, OCR, transcription, or Markdown never replaces the original Source. Keep derived output in the private batch directory unless it has an independently justified long-term role.

## Minimum locator quality

| Format | Preserve | Failure handling |
| --- | --- | --- |
| PDF | page number, text-versus-image origin, scanned-page flag | use OCR only when needed; keep table or layout uncertainty |
| DOCX | heading hierarchy, paragraphs, tables, comment/revision presence | do not present plain-text export as complete document structure |
| XLSX/CSV | sheet, cell/range, formulas versus displayed values | report merged cells, hidden rows/columns, and formula errors |
| Image | original image and OCR region or visual location | record low resolution, cropping, and obstruction |
| Audio/video | timestamps, language, transcription model/version, speaker certainty | do not turn unreliable transcription into confirmed fact |

## Chat exports

Use an official or already authorized export before considering internal databases or caches. Record account scope, stable conversation identity, reported message count, parsed count, time range, export time, and attachment placeholders. Explicitly request the full intended limit; a successful command can still return only a default subset.

For compatible WeChat-style Markdown exports, `scripts/wechat_windows.py index` creates ordered whole-day windows with line locators and message-type counts. It does not copy message bodies. Compare the parsed count with any export header; mismatch is `partial`, not complete. Attachment placeholders prove only that an attachment was mentioned, not what it contained.

Keep one continuous understanding chain for one conversation. Later windows reread the same affected objects and the previous completion receipt. Parsing can be parallel when safe, but semantic interpretation must not fragment identity or state.

## Privacy boundary

Permission to read a Source for processing does not authorize copying it into core notes or external services. Minimize credentials, identifiers, contact details, addresses, family and health information, private relationships, and unrelated emotion. If a private detail materially controls an authorized decision, keep only the minimum necessary field and its use boundary.

Adapter failure leaves the Source unchanged and creates a residue item with limitations. Do not fill missing content from filenames, placeholders, or general model knowledge.
