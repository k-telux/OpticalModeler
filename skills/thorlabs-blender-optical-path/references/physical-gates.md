# Physical gates

## Contents

1. Optical topology and ports
2. Post-first mechanics
3. CAD conversion
4. Hardware-family rules
5. Fiber, cable, and instruments
6. Platforms and rendering
7. Numeric defaults

## Optical topology and ports

- Make every visible object serve a declared experimental role. Empty posts, unknown boxes, duplicate optics, and co-located surrogates fail unless explicitly future/optional.
- Pass beams through the measured center or open aperture of every lens, filter, waveplate, pinhole, fiber coupler, objective, beamsplitter, window, and detector.
- Solve a mirror normal from incident and outgoing directions. Then roll the real mount around that normal so its mounting interface meets the support and its adjusters avoid the beam half-space.
- Solve a beamsplitter with both transmitted-axis and splitting-plane constraints. Include endpoint rays; one plane cannot create arbitrary orthogonal outputs.
- Treat every declared branch as end-to-end topology. A visually plausible main beam does not excuse a disconnected return, detector, g(1), g(2), or spectrometer branch.
- Store topology as explicit directed edges with exact port and signal-family identifiers. Do not synthesize a return edge merely because a forward edge exists; keep optional and deferred node IDs exact.
- Trace a zero-radius axis for physical clearance. A thick visible beam is presentation geometry and must be classified separately.

## Post-first mechanics

Use a continuous load path:

`verified table hole -> screw/shank/washer -> clamp -> base adapter -> post holder -> post -> real mount face/hole -> device`

- Choose the post height from the optical center and clearance before placing the mount.
- Center the post in the holder bore. Do not use a nearby cylinder as a support.
- Make the flat post top contact the mount's real bearing face. Hide the stud in the real hole; never use an exposed stud as a spacer.
- Make a fork clamp capture its own adapter. Put the washer on the slot bearing surface and the shank through the slot into a verified open table hole.
- Classify thread/hole engagement separately from illegal opaque-body collision.
- Prove raised boards and large instruments with a complete table-to-device load path and side/cutaway views.
- Anchor every serialized load witness to reopened mesh surface points or measured contact envelopes. Object origins and nominal centers are not load-path endpoints unless independently proved to lie on the intended interface.
- Send every evaluated-world-mesh AABB candidate through narrow-phase BVH before classification. Never skip a pair merely because it shares a node, family, station, table, prefix, wildcard, or regex.
- Declare allowed contacts before the audit by exact object/role pair, interface or load-link proof ID, and numeric gap/penetration envelope. Any unclassified or out-of-envelope overlap is illegal.
- Freeze a finite regeneration budget in the run spec. When it is exhausted, retain the exact illegal pairs and return `BLOCKED`; do not broaden the allowlist to force PASS.

## CAD conversion

- Read native units from the STEP/XCAF unit context. Never infer file units from a metric SKU suffix, thread standard, filename, or catalog family.
- Require finite native and transferred bboxes, non-empty faces/triangles, explicit BRep validity, and two deterministic conversion runs before calling a converter PASS.
- Record raw and cleaned mesh metrics separately. Cleanup must not erase an invalid source, empty faces, non-manifold residuals, lost assembly occurrences, or semantic-port uncertainty.
- Treat flattened assembly names as `PARTIAL_SCOPED` until occurrence hierarchy is proved. Treat surface-only models as surface-only; do not relabel them as manifold solids.
- Keep conversion status independent from packaging status. A sanitized package cannot upgrade a sentinel bbox, failed mesh, missing port frame, or blocked Blender import.

## Hardware-family rules

### KM100-style mirror mount

- Seat the mirror disk inside the real frame.
- Coincide mirror center, mount optical center, and solved beam intersection.
- Engage the real bottom or side mounting hole.
- Roll adjuster knobs away from the incident/outgoing beam region.

### LMR1-style transmissive mount

- Keep the mount vertical and the optic centered in the real bore.
- Seat the foot on the post top and keep the stud out of the glass.
- Do not add decorative external retaining rings.

### CCM1-style mounted beamsplitter

- Use physical face-port centers, not cube edges or opaque cage walls.
- Engage the bottom mount interface and preserve both transmitted and reflected branches.

### MBT/RMS objective and FC chain

- Identify the official mesh's thread segment, shoulder, seat, objective entrance, and FC center before moving it.
- Keep the large objective barrel outside the retaining seat while the declared threaded segment engages the real bore with full-circumference retention.
- Audit free-space beam -> objective entrance -> internal focusing envelope -> thin internal segment -> FC/ferrule center.
- Label a cone or waist as a schematic envelope unless the optical prescription supports a calculated Gaussian focus.
- Continue sleeve, ferrule, boot, jacket, and fiber without endpoint gaps.

### Aperture, slit, and spectrometer

- Use an annular opening, iris, pinhole ring, or two real slit blades—not a solid disk.
- Measure slit center and width from blade meshes.
- Continue the zero-radius axis through the slit and any internal redirecting optic to a detector center read from scene geometry.
- Remove duplicate entrance and sensor-window proxies. Mark a CAD-missing enclosure as modeled, not official.

## Fiber, cable, and instruments

- Give every fiber or cable named endpoint ports, tangent continuity, strain relief, and a physically plausible bend radius.
- Recheck the whole family after moving a device or platform; do not move only the decorative curve.
- A projected crossing is acceptable only when measured 3D clearance is positive.
- Keep optical beams, fiber, and electrical cables in separate materials and audit families.
- Give cameras, detectors, cryostages, and spectrometers visible feet, brackets, fasteners, and continuous load paths.

## Platforms and rendering

- Extend an accepted table by cropping/tiling the accepted or official matching mesh. Never non-uniformly scale hole geometry.
- Preserve material slots and per-polygon material indices across extensions.
- Replace layout placeholders with explainable multi-part enclosures before final acceptance.
- Use bright side/oblique, axial, and cutaway audit views. Beauty lighting cannot hide contact, aperture, collision, or support evidence.
- Keep labels near bases, away from optical centers and beam crossings. Avoid arrows and leader lines unless requested.

## Numeric defaults

Use the strictest applicable user requirement, primary-source tolerance, or manufacturer specification. Record which authority supplied each non-default threshold. Otherwise use these evidence defaults:

| Gate | Default |
|---|---:|
| Optical/mechanical center error | `<= 0.1 mm` |
| Axis alignment | `abs(dot) >= 0.9999` |
| Bearing/contact gap | `<= 0.1 mm` |
| Table-hole penetration | `>= 4 mm` |
| Representative annular support fraction | `>= 0.25` |
| Fiber/cable bend radius | `>= 30 mm` |
| Fiber/cable endpoint or join error | `<= 0.1 mm` |
| Undeclared opaque collision pairs | `0` |
