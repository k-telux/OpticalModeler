# OCT Phase 2 representative geometry smoke

This public package is the sanitized evidence bundle for the representative Phase 2 gate. The authoritative verdict is `UNVERIFIED` with `PARTIAL_SCOPED` audit scope; no full-graph propagation is authorized.

Start with [PHASE_2_REPRESENTATIVE_SMOKE_GATE.md](PHASE_2_REPRESENTATIVE_SMOKE_GATE.md), then inspect the JSON audits under `phase2/` and the four PNGs under `evidence/`. Run `python tools/validate_phase2_gate.py` from any location to recheck hashes, topology counts, render decodability, forbidden file types/magic bytes, and path sanitization.

Raw vendor CAD, derived mesh files, runtime archives/binaries, and Blend files are deliberately absent. Their exact hashes and scoped audit results are retained as non-file evidence only.
