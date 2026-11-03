# Kashi: sunrise to aarti

GOAL:    the viewer travels the Banaras riverfront in one breath, from the morning fires of
         Manikarnika to the evening aarti at Dashashwamedh, and wants to watch it again.
OUTPUT:  HyperFrames, 1080 x 1920, 30 fps
TIME:    30 s x 30 fps = 900 frames. Silent by request: no music, no effects.
LOOK:    the medium is a hand-built tabletop diorama photographed with a macro lens.
         Ground: the studio sweep behind the block, #f2e8db at sunrise, #251d44 to #0e0b1c at dusk.
         Light: sunrise key from the river side (-8, 11, 15), warm #ffd0a0 at 2.4; cool rim #9fb6d8 at 0.35.
         Dusk key from behind the town (-11, 9, -14), #ff7a52 at 0.3; lamps, pyres and windows carry the frame.
         Depth: ambient occlusion in every corner, tilt-shift blur 2.2 px per unit off a focus line at 47% height,
         vignette 0.5 (day) to 0.85 (dusk), grain 3%. Bloom only on flames, lamps, windows and diyas.
         No text on screen (by request).
OBJECTS: ghat steps of Chunar sandstone with silt below the waterline; pastel plastered houses with
         monsoon streaks, peeling brick, shutters, jharokhas, water tanks, washing; the leaning
         Ratneshwar temple standing in the river; pyres with smoke and stacked firewood at Manikarnika;
         the gold spire and dome of Kashi Vishwanath above the corridor stair; six aarti platforms with
         saffron-clad priests and tiered brass lamps; cane umbrellas; wooden boats; floating diyas.
MOTION:  one continuous camera on a time-keyed Catmull-Rom path; final segment eases out (cubic)
         into a 1 s near-hold. Light change: smoothstep from 14 s to 22 s. Aarti lamps circle at
         2 rad/s with radius 0.1 x light change. Boats, gulls, smoke, water all functions of time.
SHOTS:   0-5 s    low over the water at Manikarnika: Ratneshwar leaning out of the river in the
                  foreground, pyres burning behind, smoke drifting north. Frame 0 is the hook.
         5-10 s   glide south past the timber boats and fires at boat height.
         10-14 s  arrive at the Ganga Dwar gate of the Vishwanath corridor; crane up the stair.
         14-18 s  rise to the gold spire as the sun starts to drop.
         18-23 s  pull back high and wide: the whole riverfront as dusk falls, windows lighting.
         23-30 s  descend onto Dashashwamedh: priests circling lamps, diyas on the water, near-hold.
BANNED:  on-screen text, logos, glowing orbs or particles as decoration, cuts that break the single
         journey, a dark void with a small object in the middle (the diorama fills the frame).
QA:      t=0 (hook reads as a temple in a river at sunrise), 7, 12, 16, 20, 26, 29.9.
