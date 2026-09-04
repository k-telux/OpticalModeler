# Contributing

Contributions are welcome when they improve transferable optical, mechanical, or evidence rules.

1. Open an issue describing the experimental role, hardware family, failure mode, and evidence.
2. Keep one rule per change and distinguish universal guidance from scene-specific measurements.
3. Add or update an accepted representative case only when saved-scene readback and visual evidence agree. A limitation case is also useful if labeled as a source-review/preview record with missing evidence and physical release explicitly false; never describe it as an independent qualification run.
4. Do not commit vendor CAD, credentials, private laboratory documents, raw agent conversations, or absolute local paths.
5. Rebuild any changed example manifest, then run `python scripts/validate_repository.py` before opening a pull request. Binary decode skips, forbidden PNG metadata, stale derived counts, and manifest mismatches are release blockers.

Rule changes must preserve fail-closed semantics. If the evidence cannot prove an assembly, use `UNVERIFIED`; do not weaken a global gate to make one example pass.

Use normal Python for repository validation and ledger tests. The validator and canonical ledger reject assertion-disabling optimized modes (`-O`, `-OO`, or `PYTHONOPTIMIZE`). Run `python -m unittest discover -s tests` for the supported regression suite.

Distinguish explicit user-scope corrections, demonstrated evidence limitations, and independently repeated qualification findings. Documentation updates do not require a new modeling campaign, and do not confer physical acceptance. Keep scene-specific coordinates and visual thresholds in examples. Batch related updates into one release after the scoped checks pass.
