# Contributing

Contributions are welcome when they improve transferable optical, mechanical, or evidence rules.

1. Open an issue describing the experimental role, hardware family, failure mode, and evidence.
2. Keep one rule per change and distinguish universal guidance from scene-specific measurements.
3. Add or update a representative case only when the saved-scene readback and visual evidence agree.
4. Do not commit vendor CAD, credentials, private laboratory documents, raw agent conversations, or absolute local paths.
5. Run `python scripts/validate_repository.py` before opening a pull request.

Rule changes must preserve fail-closed semantics. If the evidence cannot prove an assembly, use `UNVERIFIED`; do not weaken a global gate to make one example pass.
