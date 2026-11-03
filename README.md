# Kashi Ghats Diorama

A tabletop-style 3D diorama of the Varanasi (Banaras) riverfront, from Harishchandra Ghat to Manikarnika Ghat,
with Dashashwamedh's evening aarti, the gold spire of Kashi Vishwanath and the leaning Ratneshwar Mahadev temple.
About 2 km of riverfront is folded into one block, so it is not to scale.

The repo has three parts that share one scene layout.

## 1. Interactive web diorama: `banaras-ghats.html`

A single-file Three.js page (r147 from jsDelivr). Drag to orbit, scroll to zoom, tap a landmark name to fly there.
Sunrise and evening-aarti modes, ambient occlusion, bloom, tilt-shift blur, procedural stone, plaster and earth
shading, water with caustics and foam.

Open it through any static server, for example:

```bash
python3 -m http.server 8000
```

then visit `http://localhost:8000/banaras-ghats.html`.

## 2. Vertical film: `ghats-film/`

A [HyperFrames](https://hyperframes.heygen.com) project that renders the same diorama as a 30 s, 1080x1920 video:
one continuous camera move from sunrise at Manikarnika to the evening aarti at Dashashwamedh. Every frame is a pure
function of time, so renders are deterministic. `SPEC.md` holds the shot plan and `REVIEW.md` the review notes.

```bash
cd ghats-film
npx hyperframes preview     # Studio preview
npx hyperframes render -q delivery -o renders/kashi-sunrise-to-aarti.mp4
```

## 3. Blender test: `blender-test/`

An experiment in rendering the same scene with Cycles for photographic materials, water and volumetric smoke.

- `export.html` exports the three.js scene to `diorama.glb` plus `scene_info.json` (fires, lamps, diyas, boats).
  Serve the repo root with `python3 blender-test/serve.py 8766` and open
  `http://localhost:8766/blender-test/export.html`; the page writes both files back into `blender-test/`.
- `build.py` imports the GLB into Blender, rebuilds every material with CC0 textures from
  [Poly Haven](https://polyhaven.com) (in `textures/`), adds a water volume, smoke, fire, lights and the film's camera
  path, then renders one still:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender-test/build.py -- --t 1 --out "$PWD/blender-test/renders/t01.png"
```

`render_stills.sh` renders three matching stills (sunrise, gold spire, aarti). Status: work in progress. The exporter
was fixed to split multi-material meshes, which removes holes in the ghat steps and courtyard; stills have not been
re-rendered since that fix.

## Credits

Textures: Poly Haven (CC0). Fonts: Rozha One and Hind by Indian Type Foundry (SIL Open Font License).
