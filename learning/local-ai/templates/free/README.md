# FREE JSON Part template contract

FREE production uses exactly five bounded content slots. Each accepted Part belongs to exactly one slot and must not act as a general prompt dump.

## Common rules

- `document_type` is always `local-rag/json-part`.
- Local AI emits `status: staging`; only the user/application acceptance path may promote it to `accepted`.
- `payload.generation.positive` and `payload.generation.negative` are the only generation strings consumed from a canonical JSON Part today.
- `payload.structured` exists to preserve machine-readable intent for future validation/compiler work. It must agree with the generation strings.
- `application.mode` is `delta` by default: explicitly stated fields override/augment the MAIN image or other authorities only inside that slot's domain; unspecified details are preserved.
- Do not repeat unrelated authorities into a Part merely to make the prompt longer.
- Pose is owned by the POSE image / DWPose-ControlNet, not by these five Parts.
- Drawing method is owned by Rendering Authority, not by these five Parts.
- Contour strength is owned by Lineart Authority, not by these five Parts.
- Camera/composition and background are separate slots even when both affect spatial appearance.

## Slot ownership

### `character_body`
Owns explicit physical appearance/body deltas: hair, eyes, skin color, build, proportions, anatomy-level appearance and other intrinsic subject traits.
Must not define outfit, facial expression/state, pose, camera, background or rendering style.

### `outfit_prop`
Owns garments, accessories and intentionally depicted props associated with the subject.
Must not redefine body shape, expression, pose, camera, background or rendering style.

### `expression_face`
Owns temporary facial state: gaze, eyelids, brows, mouth shape, blush/tears and expression-level facial changes.
Must not redefine facial identity, hair, body, pose, camera, background or rendering style.

### `camera_composition`
Owns framing, crop, camera angle/elevation, perspective/lens-like view and subject placement in frame.
Must not define skeletal pose, character appearance, outfit, expression, scene content or rendering style.

### `background_scene`
Owns location/environment, environmental objects, time/weather and scene-specific illumination source/context.
Must not define the drawing technique, line strength, character appearance, skeletal pose or camera mechanics.

## Authority precedence

Authority is resolved by domain rather than by one global prompt winner:

1. Rendering Authority is strongest for **how the image is drawn**.
2. Lineart Authority is strongest for **contour clarity/line strength**.
3. POSE image is strongest for **skeletal posture and limb placement**.
4. MAIN image is strongest for **appearance that is not explicitly changed by a role-bound JSON delta**.
5. A JSON Part wins only for an **explicit delta inside its own slot domain**.
6. Unspecified details should be preserved rather than invented as overrides.

Templates in this directory are normative examples for local-AI generation.