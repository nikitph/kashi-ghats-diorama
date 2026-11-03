# Review: Kashi, sunrise to aarti (1080 x 1920, 30 s, silent)

## Creative calls
- One continuous camera move, no cuts, north to south: Ratneshwar and the Manikarnika fires at
  sunrise, the corridor gate and stair, a crane up to the gold Vishwanath spire, a high pull-back
  as dusk falls (14-22 s), then down onto the Dashashwamedh aarti with diyas on the river.
- The scene is the interactive diorama itself, rebuilt so every frame is a pure function of time
  (water, fires, smoke, embers, boats, gulls, diyas, lamp circles, camera, light change).
  SSAO kernels are seeded so parallel render workers produce identical frames.
- Not built: a landmark-by-landmark version with name cards (you asked for no text), and a
  version with a music bed (you asked for silence).

## Measured vs looked at
- `check` passes. Kept warnings: `film_silent` (silent by request), `canvas_content_at_edge`
  (full-bleed 3D canvas by design), `composition_file_too_large` (one 3D scene in one file).
- Looked at frames 0, 4, 7, 12, 16, 20, 23, 24, 25, 27, 29.9 across four review passes.
  Fixed: hook framing too tight at 0 s, crane grazing the gate at 12 s, an overexposed ending,
  an ending that missed the river and grazed a boat canopy.
- Not checked frame by frame: every in-between frame; motion smoothness is judged from the render.

## Weakest shot
- 23-24 s: a gull passes close to the lens and reads as a white paper triangle. With more time:
  give the gulls a body and keep them above 5 units.
