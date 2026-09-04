# Fresh measurement design and render fidelity

Use this reference when an old model is a quality comparator, the requested measurement is new, or a preview fails to show usable optics. These rules clarify user intent and evidence limits; they do not make one laboratory's parts, colors, coordinates, or image thresholds universal.

## Choose the operation from the request

| Request | Starting point | Required change |
|---|---|---|
| Reconstruct this schematic | The supplied topology and declared sources | Map its measurement roles into a supported 3D assembly. |
| Correct this model | Its frozen scene and the latest correction | Change affected geometry and invalidate dependent evidence. |
| Render this accepted model | Its verified geometry | Change presentation and retain an explicit geometry comparison. |
| Build another measurement at this example's quality | A new measurement definition and an empty scene | Derive a new topology; use the old example only for declared visual comparisons. |

State the selected modality, source, measured quantity, sample interaction, reference/calibration path, and detector outputs before geometry. If the user allows another measurement without specifying one, choose a suitable concrete design and state the assumption. A Mach–Zehnder interferometer is one option, not a required default or a proven instrument simply because it has two arms.

Classify references as design authority, reusable component assets, visual comparators, or historical diagnostics. A visual comparator supplies targets such as silhouette detail, material readability, composition, and output resolution; it grants neither topology nor acceptance credit.

## Build independently with reusable components

For a fresh design, start with factory-empty Blender data and a new run, topology, generator, and scene. Do not copy/append/link a prior complete scene, rename its objects, or filter away electronics and call the result a new design. Load only explicitly permitted component assets from their recorded sources. Reusing a canonical mount is different from inheriting the old apparatus.

Assign each instance a new role, transform, optical-port binding, and support path. Record source file identity, native units, local axes, optical anchors, official/modeled status, and license boundary. Recheck assembly interfaces after placement. Localizing datablocks does not erase provenance or grant redistribution rights.

Prove independence with the actual asset load list and generator inputs, followed by saved-scene library/datablock and role inventory. An empty `bpy.data.libraries` list, new names, or a different Blend hash alone is insufficient: appended old geometry can also be local and renamed. When self-contained assets are required, confirm all intended data are local; otherwise document any explicitly allowed dependency.

## Respect optics-only scope

When requested, include sources, optical elements, sample stages, optical detector bodies, optically necessary fiber, and real mounts/supports. Omit power/signal/data cables, circuit boards, timing electronics, racks, and unrelated control boxes from scenes, exports, and renders. Preserve excluded source records as metadata only if needed; do not use older electrical counts to expand the new visible scope.

User-facing views must not depend on empties, relationship lines, bounds, axes, helper frames, or unexplained blocks. A hidden helper is acceptable for implementation if its purpose is declared; it is not a physical device. Check at least a complete top view and an oblique view so that source, sample interaction, branches, recombination, and detector endpoints can be followed.

## Separate design arithmetic from physical proof

- Compute design arm lengths and surface-normal solutions from the topology. Label them as design values until tied to the actual saved assembly. Geometric arm length is not optical path length through glass, and equal arms do not establish interference contrast or measurement calibration.
- Derive endpoint error from an actual reopened port or surface witness. Copying a target coordinate to both sides of a subtraction, assigning `0.0`, or copying a manifest value is not a measurement.
- Identify the intended optical face, aperture, or detector plane at each transition. A ray hitting an object with the expected role could have hit the mount or opaque housing instead. Record hit object, polygon/surface, world position, normal, and distance against the permitted interface.
- Do not skip every member of the source family. Limit any self-intersection offset/exclusion to the declared launch surface and record its extent. A missed required endpoint stays `UNVERIFIED` or `BLOCKED` even when the unexpected-hit count is zero.
- Keep generator-time checks, saved-scene checks, global narrow-phase BVH, and mechanical load-path proof distinguishable. A reflection-vector calculation or illustrative ray trace cannot supply missing mesh/assembly evidence.

For interferometers, resolve both splitter transmissions/reflections and required outputs explicitly. Record polarization/coherence/path-length assumptions and the modeled optical regime. Arm colors may identify routes; do not imply different wavelengths merely because diagnostic colors differ.

## Match fidelity at the component and image levels

Use a small set of comparable component close-ups alongside the whole apparatus. Compare silhouette, real subparts, adjusters, mount openings, optic seating, fasteners, table holes, and sharp mechanical edges at similar on-screen scale. More objects, more render samples, or smoother shading cannot substitute for missing geometry.

When surfaces look crumpled, faceted, or unexpectedly metallic, identify the responsible mesh/solid, coincident faces, normals, and material assignment. Apply the smallest correction that preserves dimensions and intended edges. Preserve polygon material indices when changing table or mount palettes. Do not obscure a defect with darkness, blur, bloom, or a flattering camera.

Use a restrained palette, readable anodized edges, controlled metal highlights, modest glass, and thin beam cores with subdued halos. Review a low-resolution draft for complete framing and clipping before expensive output. Save the selected presentation settings and bind render receipts to the actual scene and image. Camera-only improvements should not trigger a rebuild of unchanged CAD or physics.

Image QA needs two levels:

1. Global checks: actual decoded dimensions/bit depth, clipping, blank regions, and broad detail diagnostics.
2. Role-specific checks: projected beam/port regions, component close-ups, and full-path visual inspection. Segment the declared beam families inside expected regions; exclude the colored background and table. Inspect the segmentation overlay and report branch endpoints/gaps. Generic saturation masks, colored-pixel totals, skeleton length, and global Canny/Laplacian values cannot establish branch continuity.

Thresholds depend on framing, lighting, scale, and resolution. Keep them with the example that justified them. A change in camera framing that increases edge density is not evidence of improved mesh precision. Record visual diagnostic PASS separately from optical/physical PASS. A requested 4K deliverable must be rendered at its declared 4K dimensions; a 2048-wide image remains a preview even when saved at 16-bit depth.

## Finish efficiently and preserve a useful checkpoint

Keep one scene writer. When parallel work is authorized, assign independent source/optical/mechanical/visual reviews with explicit input and output scopes; do not send private context to public-only tests. Schedule GPU rendering and CPU work according to actual memory/device capacity instead of running competing heavy jobs blindly.

Verify immutable identities at stage boundaries and after suspected changes. Reuse successful checks only while their inputs, runtime, and dependency set remain unchanged; retain exact final manifests and physical checks. When runtime bytes change at the same path, preserve the old report, invalidate affected evidence, and use an explicitly selected compatible runtime or document a replacement within existing authority. Keep CAD/OCP, Blender, and OpenCV dependency environments isolated.

For a pause or handoff, record the current candidate, last completed gate, pending checks, active processes, and next reproducible command. Transfer sole-writer ownership only after the prior writer stops. Do not count stale source snapshots as current after later edits.

Stop at the first candidate meeting the user's declared deliverables and hard gates. Batch related fixes, reuse unchanged source acquisition, and defer nonblocking polish. If only a preview is complete, deliver it with the exact remaining work instead of claiming final quality. A documentation release can publish these lessons without launching another modeling campaign or certifying the example.
