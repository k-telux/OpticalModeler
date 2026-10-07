# Presentation, image provenance, and usable delivery

Use for accepted geometry that needs readable views, controlled materials/light, or a clean final package. Presentation acceptance does not establish a new physical or experimental verdict.

## Preserve the actual saved scene

Freeze the engineering package and its delivery pointer. Work in an explicitly separate presentation copy. Declare the allowed shaders, lights, world, exposure, compositor, cameras and nonphysical backdrop; protect all other dependencies.

Read the source and candidate after saving. Compare the complete relevant stored and evaluated data across every applicable state:

- exact object/data/collection sets, world transforms, local meshes and curve centerlines/radii;
- polygon boundaries, vertices, edges, loop topology, material slots and per-polygon indices;
- sharp flags, custom/packed corner normals and all present mesh attributes;
- modifiers, constraints, animation, custom properties, optical ports and support metadata;
- collection/layer/render/ray visibility and state-specific active edges;
- protected shader graphs, light/world/compositor/view settings and camera parameters.

The comparison may allow a precisely declared subset, such as five non-optical object-slot overrides. Sparse vertex fingerprints, object counts or loop indices alone do not prove preservation. Read attributes according to their actual native types; an unsupported present field stays unverified rather than being silently skipped. Choose the comparison depth appropriate to the claimed preservation, and expose omissions.

## Diagnose materials before changing the palette

A material named "black" can have a pale shader. Inspect actual object-to-slot-to-face bindings, base color, roughness, specular/metallic settings and shared users. Copy a shared material for the intended object/slot when necessary; do not darken a sensing face, optical coating or another device accidentally.

Wrinkled shading or unexplained silver patches may come from duplicate surfaces, incorrect solid partitioning, normals or a wrong STEP material assignment. Correct the identified cause while preserving dimensions and working surfaces. More global samples, blur, darkness or blanket smoothing cannot repair that defect.

Use the accepted scientific beam palette and modest halos. Lower enclosure glare through scoped shaders and lights. Do not increase beam radius, invent a branch, hide hardware, or change accepted cameras unless the request allows it. If reference images are requested, select actual optical-path figures/covers, record source links and transferable composition principles, and do not redistribute their pixels or imply journal endorsement.

## Review actual images

Start with bounded low-cost previews. Verify camera/view clipping against the actual coordinate scale and execute a small render/decode on the selected GPU before expensive output. Device enumeration is not kernel-execution evidence. Keep one heavy GPU owner and respect real RAM/VRAM headroom and user-declared stop boundaries.

Inspect actual results at two levels:

1. Decode the delivered image, check dimensions, encoded bit depth, clipping, blank regions and broad exposure/detail.
2. Inspect device/port regions, each branch and the full path against the requested view. Use OpenCV or equivalent analysis as assistance, followed by task-specific visual interpretation.

A target inside a camera frame can still be fully occluded. Orthographic occlusion uses parallel viewing rays, not rays toward the camera position. Choose a complementary lower/side view to reveal stacked optics; do not remove the upper platform to manufacture a clear full-system view. Show whole-apparatus views plus close-ups that add distinct evidence.

Temporary diagnostic filtering is limited to declared nonphysical display objects, with hardware unchanged and filtering disclosed. Select the state first and check evaluated visibility after rendering: frame animation can restore hidden curves. Review the actual final filtered image. A rejected first image and its hash never become the accepted output.

## Reuse images honestly

Every image receipt identifies the actual producing saved scene, render settings, view/state, any temporary camera/display overrides and image hash.

If a camera alone changes, rerender its affected view. An unchanged old image can be retained only after preserving its original producer identity and proving that its relevant dependencies remain equivalent: apparatus, state, beam geometry/visibility, that camera, materials, lights/world, compositor and backdrop. Record a fresh preservation bridge with scope and omissions. Do not rewrite an old receipt to say the image was newly rendered from the current Blend.

An explicitly recolored/re-lit presentation requires fresh output for every affected view. File timestamps, familiar filenames and a new manifest are not proof of a fresh render.

## Deliver the user-facing result

Use a clean delivery folder containing the requested editable engineering/presentation files, actual final images, concise viewing guide, assumptions/measurement checklist and a manifest as appropriate. Keep failures, source caches, helper scripts, old images, automatic backups and reviewer working files outside the clean handoff. Do not automatically generate a PDF, GLB, ZIP or email when it was not requested; if delivered, each adds its own validation requirements.

For an interactive Blend, save a readable perspective workspace, sensible orbit center and clipping, with accessible overview/top/branch views. Verify the actual reopened UI with final-state screenshots, image recognition and realistic navigation where the task requires it. A successful launch or a gizmo action does not prove an untested middle-button drag. Preserve user-wide preferences and unsaved GUI work; background disk reads do not validate the GUI.

In the final reply:

- lead with the concrete delivered change and its scope;
- link every artifact the user should open using clickable Markdown and absolute local targets;
- show the actual requested result image when helpful, keeping private media local;
- distinguish saved-model checks, actual image inspection, interactive UI tests and physical unknowns;
- capture the rendered final reply if the environment supports it, check the result and link affordances, and audit that it proves the original task outcome.

If final-reply capture is unavailable, state `reply_visual_confirmation=incomplete`. Markdown source and a tool output are not visual confirmation of the user's rendered reply. This does not erase separate verified model/image evidence.

Hash final files after all writes, resolve the current delivery through its scope-specific pointer, and freeze the first package that meets the declared task. Optional aesthetic variants go to a later request.
