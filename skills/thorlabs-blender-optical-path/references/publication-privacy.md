# Publishing laboratory-derived skills and examples

Use when the user authorizes public release of guidance derived from private laboratory work. Authorization to publish a skill does not automatically authorize publishing the underlying photographs, models, exact setup or raw chat history.

## Preserve private evidence; curate a public derivative

Keep the private project, source photos, CAD cache, saved models, full identity matrix, audits and correspondence unchanged. Publish from the separate curated repository. Extract decisions and failure patterns; never copy the entire project, session dump or project memory into Git.

Use consistent role aliases for laboratory instruments, such as `SOURCE_A`, `DELAY_STAGE`, `SPECTROGRAPH`, `DETECTOR_BACK`, `DETECTOR_SIDE_PROPOSED`, `ENTRANCE_SHUTTER` and `RELAY_LENS`. The private mapping from aliases to real brands/SKUs stays outside the public tree. Keep installed, proposed, reference and unknown statuses visible in the public explanation.

Public-catalog part numbers in previously published, source-backed independent examples may remain for reproducibility. Do not connect them to private installed inventory. A privacy request about a laboratory setup is not a reason to fabricate substitute official part numbers or silently corrupt historical CAD locks.

## Redact the setup, not only a sentence

| Private content | Public treatment |
|---|---|
| Important source, delay, spectrometer and camera identities; unique lens/attenuator combinations | Stable functional aliases without exact manufacturer/SKU, suffix or private URL. |
| Surveyed positions, operating wavelengths/powers, calibration and distinctive layout dimensions | Omit or use explicitly illustrative parameters unrelated to the installed setup. |
| Nameplates, serial numbers, asset tags, room/institution identifiers and faces | Exclude the laboratory photo; use an already approved public example or an independent teaching illustration. |
| Object/collection/material names, filenames, captions, JSON/CSV records and diagrams | Check for identifiers and indirect reconstruction of the alias map. |
| Personal paths, email addresses, user IDs, session/thread IDs and tokens | Remove from public content and release/commit text. |
| Vendor CAD, converted meshes and proprietary/lab Blends | Exclude unless separate redistribution and distribution authorization is established. |
| Private hashes and raw reviewer transcripts | Keep privately; publish scoped lessons or edited examples, not a searchable private identity trail. |

Removing visible labels from a highly recognizable apparatus image may still expose the setup. Prefer no private laboratory image over a weak cosmetic redaction. Inspect pixels of every newly public visual, not only its text or metadata. Generic drawings are labeled as illustrative rather than passed off as the private final model.

Dialogue examples must say they are edited/anonymized teaching reconstructions. Preserve the consequential interaction: initial request, relevant clarification, user correction, revised constraint, checks, final output and remaining unknowns. Do not invent verbatim quotes, precise measurements, new screenshots or a successful result that the source does not support.

## Scan the final candidate

Keep a private UTF-8 list of sensitive terms outside the repository, one nonempty term per line, including real model aliases/variants, personal identifiers and any known isolation markers. Include punctuation/case variants when relevant. Do not print the list or include it in CI artifacts.

Run the existing repository validator with normal Python, then add the private list locally:

```text
python scripts/validate_repository.py --private-terms-file /private/release-inputs/sensitive-terms.txt
```

The optional scanner checks candidate relative filenames and every file's uncompressed bytes in UTF-8, UTF-16LE and UTF-16BE, allowing case and common model-separator variations. A match reports a path without echoing the term. This is a bounded literal/normalized identifier check, not OCR, secret discovery, archive expansion or proof that rendered pixels hide every identifying detail. The validator rejects vendor scene/CAD files and the existing PNG parser checks forbidden metadata. Inspect permitted binary/container content separately as applicable.

Check all candidate files, not just changed Markdown. Parse image/document/container metadata, strip metadata only from public copies, preserve pixels when doing metadata-only sanitization, and regenerate dependent hashes. Scan new commit/tag/release prose too. Build example manifests last; postscan must be read-only. Keep scan evidence outside the public tree when it contains private policy inputs.

The release-head scan does not erase previously public Git history, old tags, forks or downloads. Do not rewrite history or force-push as a routine update; a discovered historical exposure requires a separately scoped remediation decision.

## Release and verify

Synchronize the canonical English skill, Chinese/Japanese entries, README entry points, version metadata and installed skill. Preserve the supported invocation policy and unrelated interface fields. Validate frontmatter, links, package file sets, hashes, existing example verdicts and changed scripts before publishing.

A documentation/software release can publish generalized scope rules and explicit limitations without a new optical-model campaign. Do not claim fresh blind testing, repeatable performance or physical qualification from source review. Retain historical failed/scoped verdicts and label the new release accordingly.

Commit only the curated public tree, use an immutable version tag, push the authorized branch/tag, then read back remote identities and CI. Report the actual repository, version, commit and validation scope. If a remote operation is ambiguous, inspect its result before retrying; a failed upload cannot be reported as published.
