"""Build the Kashi ghats diorama in Blender from the three.js export and render one still.

Run:  Blender -b -P build.py -- --t 1.0 --out renders/t01.png [--samples 96] [--scale 100] [--save kashi.blend]
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'textures')

# ---------------------------------------------------------------- arguments
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default
T_SEC = arg('--t', 1.0)
OUT = arg('--out', os.path.join(HERE, 'renders', 'still.png'))
SAMPLES = arg('--samples', 96)
SCALE = arg('--scale', 100)
SAVE = arg('--save', '')

def lerp(a, b, t): return a + (b - a) * t
def smooth(e0, e1, x):
    k = min(1, max(0, (x - e0) / (e1 - e0))); return k * k * (3 - 2 * k)
def mixc(a, b, t): return tuple(lerp(x, y, t) for x, y in zip(a, b))
def T(v):  # three.js (x, y up, z toward river) -> blender (x, y, z up)
    return Vector((v[0], -v[2], v[1]))
def hex2lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

M = smooth(14, 22, T_SEC)   # 0 = sunrise, 1 = evening aarti (same curve as the video)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'diorama.glb'))
info = json.load(open(os.path.join(HERE, 'scene_info.json')))

# ---------------------------------------------------------------- texture helpers
_imgs = {}
def img(name, kind):
    path = os.path.join(TEX, f'{name}_{kind}.jpg')
    if not os.path.exists(path) or os.path.getsize(path) < 1000: return None
    key = (name, kind)
    if key not in _imgs:
        im = bpy.data.images.load(path)
        im.colorspace_settings.name = 'sRGB' if kind == 'diff' else 'Non-Color'
        _imgs[key] = im
    return _imgs[key]

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bsdf

def world_coords(nt, scale):
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(geo.outputs['Position'], mp.inputs['Vector'])
    return mp.outputs['Vector']

def tri(nt, vec, image):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = image
    n.projection = 'BOX'; n.projection_blend = 0.25
    nt.links.new(vec, n.inputs['Vector']); return n

def vcolor(nt):
    a = nt.nodes.new('ShaderNodeAttribute'); a.attribute_name = 'Color'; a.attribute_type = 'GEOMETRY'
    return a.outputs['Color']

def textured(name, tex, scale, tint=None, use_vc=False, avg=0.45, tex_mix=0.25, rough=None,
             normal=0.8, grime=0.0, streaks=0.0, wetline=False):
    """Principled material: texture brightness carries the detail, the three.js colour carries the hue."""
    m, nt, bsdf = new_mat(name)
    L = nt.links
    vec = world_coords(nt, scale)
    d = img(tex, 'diff'); col_out = None
    base = nt.nodes.new('ShaderNodeRGB'); base.outputs[0].default_value = (*(tint or (1, 1, 1)), 1)
    hue = base.outputs[0]
    if use_vc:
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1
        L.new(hue, mul.inputs['A']); L.new(vcolor(nt), mul.inputs['B']); hue = mul.outputs['Result']
    if d:
        dn = tri(nt, vec, d)
        bw = nt.nodes.new('ShaderNodeRGBToBW'); L.new(dn.outputs['Color'], bw.inputs['Color'])
        k = nt.nodes.new('ShaderNodeMath'); k.operation = 'DIVIDE'; k.inputs[1].default_value = avg
        L.new(bw.outputs['Val'], k.inputs[0])
        sh = nt.nodes.new('ShaderNodeMix'); sh.data_type = 'RGBA'; sh.blend_type = 'MULTIPLY'; sh.inputs['Factor'].default_value = 1
        L.new(hue, sh.inputs['A']); L.new(k.outputs['Value'], sh.inputs['B'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['Factor'].default_value = tex_mix
        L.new(sh.outputs['Result'], mx.inputs['A']); L.new(dn.outputs['Color'], mx.inputs['B'])
        col_out = mx.outputs['Result']
        r = img(tex, 'rough')
        if r and rough is None:
            rn = tri(nt, vec, r); L.new(rn.outputs['Color'], bsdf.inputs['Roughness'])
        if normal > 0 and not os.environ.get('NOBUMP'):
            bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35 * normal
            bp.inputs['Distance'].default_value = 0.02
            L.new(bw.outputs['Val'], bp.inputs['Height']); L.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    else:
        col_out = hue
    if rough is not None or not d: bsdf.inputs['Roughness'].default_value = rough if rough is not None else 0.85
    # monsoon streaks: stretched noise running down the walls
    if streaks > 0:
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        sc = nt.nodes.new('ShaderNodeMapping'); sc.inputs['Scale'].default_value = (9, 9, 0.7)
        L.new(geo.outputs['Position'], sc.inputs['Vector'])
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 4
        L.new(sc.outputs['Vector'], nz.inputs['Vector'])
        ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[1].position = 0.75
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1); ramp.color_ramp.elements[1].color = (1 - streaks, 1 - streaks * 0.9, 1 - streaks * 1.05, 1)
        L.new(nz.outputs['Fac'], ramp.inputs['Fac'])
        st = nt.nodes.new('ShaderNodeMix'); st.data_type = 'RGBA'; st.blend_type = 'MULTIPLY'; st.inputs['Factor'].default_value = 1
        L.new(col_out, st.inputs['A']); L.new(ramp.outputs['Color'], st.inputs['B']); col_out = st.outputs['Result']
    # dirt gathered in corners
    if grime > 0 and not os.environ.get('NOAO'):
        ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.25; ao.samples = 8
        gm = nt.nodes.new('ShaderNodeMix'); gm.data_type = 'RGBA'; gm.blend_type = 'MULTIPLY'
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
        L.new(ao.outputs['AO'], inv.inputs[1])
        fac = nt.nodes.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = grime
        L.new(inv.outputs['Value'], fac.inputs[0]); L.new(fac.outputs['Value'], gm.inputs['Factor'])
        gm.inputs['B'].default_value = (0.25, 0.2, 0.16, 1)
        L.new(col_out, gm.inputs['A']); col_out = gm.outputs['Result']
    # silt and damp just above the river, algae below it
    if wetline:
        geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        L.new(geo.outputs['Position'], sep.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.65; mr.inputs['From Max'].default_value = -0.05
        L.new(sep.outputs['Z'], mr.inputs['Value'])
        wm = nt.nodes.new('ShaderNodeMix'); wm.data_type = 'RGBA'; wm.blend_type = 'MULTIPLY'
        L.new(mr.outputs['Result'], wm.inputs['Factor']); wm.inputs['B'].default_value = (0.42, 0.36, 0.27, 1)
        L.new(col_out, wm.inputs['A']); col_out = wm.outputs['Result']
    hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 1.3
    L.new(col_out, hs.inputs['Color']); L.new(hs.outputs['Color'], bsdf.inputs['Base Color'])
    return m

def plain(name, color, rough=0.8, use_vc=False, metal=0.0, sheen=0.0, sss=0.0):
    m, nt, bsdf = new_mat(name)
    rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = (*color, 1)
    out = rgb.outputs[0]
    if use_vc:
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
        nt.links.new(out, mul.inputs['A']); nt.links.new(vcolor(nt), mul.inputs['B']); out = mul.outputs['Result']
    nt.links.new(out, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Metallic'].default_value = metal
    if sheen: bsdf.inputs['Sheen Weight'].default_value = sheen
    if sss:
        bsdf.inputs['Subsurface Weight'].default_value = sss
        nt.links.new(out, bsdf.inputs['Base Color'])
    return m

def emissive(name, color, strength):
    m, nt, bsdf = new_mat(name)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Strength'].default_value = strength
    return m

# ---------------------------------------------------------------- material library
LIB = {}
def lib(key, fn):
    if key not in LIB: LIB[key] = fn()
    return LIB[key]

SANDSTONE, PLASTER, EARTH, PEBBLES, PLANKS, CONCRETE, ROCK = (
    'large_sandstone_blocks', 'painted_plaster_wall', 'brown_mud_rocks_01', 'ganges_river_pebbles',
    'old_planks_02', 'concrete_wall_003', 'coast_sand_rocks_02')

def material_for(src_name, has_vc, obj_name):
    """Map a three.js material name ('k<kind>|#hex', 'gold', ...) or instanced batch to a Blender material."""
    o = obj_name.split('.')[0]
    if o.startswith('inst_'):
        b = o[5:]
        if b == 'trim':   return lib('trim', lambda: textured('trim', PLASTER, 0.9, (1, 1, 1), True, 0.62, 0.1, normal=0.5, grime=0.5, streaks=0.25))
        if b in ('frameA', 'leaf'): return lib('paint', lambda: textured('paint', PLANKS, 1.6, (1, 1, 1), True, 0.45, 0.05, rough=0.55, normal=0.4))
        if b in ('paneA', 'paneB'): return lib('glass', lambda: plain('glass', (0.02, 0.018, 0.016), 0.12))
        if b in ('litA', 'litB'): return lib('lit', lambda: emissive('lit', (1.0, 0.55, 0.2), lerp(0, 9, M)))
        if b == 'rail':   return lib('rail', lambda: plain('rail', (1, 1, 1), 0.45, True, metal=0.6))
        if b == 'cloth':  return lib('cloth', lambda: plain('cloth', (1, 1, 1), 0.9, True, sheen=0.6))
        if b in ('bloom', 'foliage', 'grass'): return lib('leafy', lambda: plain('leafy', (1, 1, 1), 0.7, True, sss=0.15))
        if b == 'pot':    return lib('pot', lambda: textured('pot', CONCRETE, 3.0, (1, 1, 1), True, 0.5, 0.0, normal=0.4))
        if b == 'log':    return lib('logs', lambda: textured('logs', PLANKS, 2.0, (1, 1, 1), True, 0.42, 0.1, normal=1.0))
        if b == 'ash':    return lib('ash', lambda: plain('ash', (1, 1, 1), 1.0, True))
        if b == 'body':   return lib('body', lambda: plain('body', (1, 1, 1), 0.85, True, sheen=0.5))
        if b == 'head':   return lib('head', lambda: plain('head', (1, 1, 1), 0.6, True, sss=0.2))
        if b.startswith('rock'): return lib('rock', lambda: textured('rock', ROCK, 1.2, (1, 1, 1), True, 0.42, 0.35, normal=1.2))
    n = src_name.split('.')[0]
    if n == 'gold':  return lib('gold', lambda: plain('gold', (1.0, 0.7, 0.28), 0.22, metal=1.0))
    if n == 'lit':   return lib('lit', lambda: emissive('lit', (1.0, 0.55, 0.2), lerp(0, 9, M)))
    if n == 'glass': return lib('glass', lambda: plain('glass', (0.02, 0.018, 0.016), 0.12))
    if n == 'flame_outer': return lib('fo', lambda: emissive('flame_outer', (1.0, 0.3, 0.04), lerp(6, 14, M)))
    if n == 'flame_inner': return lib('fi', lambda: emissive('flame_inner', (1.0, 0.62, 0.18), lerp(10, 22, M)))
    if n.startswith('k') and '|' in n:
        kind, hexc = n[1:].split('|'); kind = int(kind); c = hex2lin(hexc)
        if kind == 0:  return lib(n, lambda: textured(n, SANDSTONE, 0.55, c, has_vc, 0.42, 0.06, normal=1.0, grime=0.6, wetline=True))
        if kind == 1:
            if hexc.lower() == '#b9ab98': return lib(n, lambda: textured(n, CONCRETE, 0.7, c, has_vc, 0.5, 0.15, normal=0.6, grime=0.4))
            return lib(n + str(has_vc), lambda: textured(n, PLASTER, 0.9, c, has_vc, 0.62, 0.03, normal=0.5, grime=0.5, streaks=0.3))
        if kind == 2:  return lib('earth', lambda: textured('earth', EARTH, 0.6, (0.75, 0.6, 0.48), False, 0.4, 0.5, normal=1.2))
        if kind == 3:
            if has_vc: return lib('rock', lambda: textured('rock', ROCK, 1.2, (1, 1, 1), True, 0.42, 0.35, normal=1.2))
            return lib('bed', lambda: textured('bed', PEBBLES, 0.8, (0.8, 0.75, 0.65), False, 0.4, 0.5, normal=1.0))
        # plain three.js colours: wood, cloth, iron
        lum = sum(c) / 3
        if lum < 0.12 and c[0] > c[2]:
            return lib(n, lambda: textured(n, PLANKS, 1.4, c, has_vc, 0.42, 0.1, normal=0.8))
        return lib(n + str(has_vc), lambda: plain(n, c, 0.75, has_vc))
    return None

for ob in list(scene.objects):
    if ob.type != 'MESH': continue
    me = ob.data
    has_vc = len(me.color_attributes) > 0
    if has_vc and me.color_attributes[0].name != 'Color': me.color_attributes[0].name = 'Color'
    for i, slot in enumerate(ob.material_slots):
        if not slot.material: continue
        src = slot.material
        has_tex = src.use_nodes and any(nd.type == 'TEX_IMAGE' for nd in src.node_tree.nodes)
        if has_tex:  # painted signs: keep their artwork, make them matte
            for nd in src.node_tree.nodes:
                if nd.type == 'BSDF_PRINCIPLED': nd.inputs['Roughness'].default_value = 0.9
            continue
        nm = material_for(src.name, has_vc, ob.name)
        if nm: slot.material = nm

# wires and washing lines: imported as loose edges, turned into thin cables
for ob in list(scene.objects):
    if ob.type == 'MESH' and len(ob.data.polygons) == 0 and len(ob.data.edges) > 0:
        with bpy.context.temp_override(selected_objects=[ob], selected_editable_objects=[ob], active_object=ob, object=ob):
            bpy.ops.object.convert(target='CURVE')
        ob.data.bevel_depth = 0.0045; ob.data.bevel_resolution = 1
        ob.data.materials.clear(); ob.data.materials.append(lib('wire', lambda: plain('wire', (0.02, 0.018, 0.016), 0.5)))

# ---------------------------------------------------------------- moving things at this moment
for i, mv in enumerate(info['movers']):
    ob = bpy.data.objects.get(f'mover_{i}')
    if not ob: continue
    a = mv['a'] + mv['sp'] * 2.5 * T_SEC
    x, z = mv['rx'] * math.cos(a), mv['zc'] + mv['rz'] * math.sin(a)
    dx, dz = -mv['rx'] * math.sin(a), mv['rz'] * math.cos(a)
    ob.location = T((x, 0.015, z)); ob.rotation_mode = 'XYZ'; ob.rotation_euler = (0, 0, math.atan2(-dz, dx))
for i, (x, y, z) in enumerate(info['aarti']):
    ob = bpy.data.objects.get(f'aartilamp_{i}')
    r = 0.1 * M; ph = T_SEC * 2.0
    if ob: ob.location = T((x + r * math.cos(ph), y + r * math.sin(ph), z))

# ---------------------------------------------------------------- the river: one water volume with a moving surface
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=240, y_segments=95, size=0.5)
for v in bm.verts: v.co = Vector((v.co.x * 24, v.co.y * 9.5 - 4.25, 0.0))
ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.z = -2.2
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
wme = bpy.data.meshes.new('water'); bm.to_mesh(wme); bm.free()
water = bpy.data.objects.new('water', wme); scene.collection.objects.link(water)
vg = water.vertex_groups.new(name='top'); vg.add([v.index for v in wme.vertices if v.co.z > -0.01], 1.0, 'REPLACE')
tx = bpy.data.textures.new('ripples', 'CLOUDS'); tx.noise_scale = 0.35; tx.noise_depth = 2
dm = water.modifiers.new('ripples', 'DISPLACE'); dm.texture = tx; dm.strength = 0.035; dm.mid_level = 0.5
dm.vertex_group = 'top'; dm.texture_coords = 'GLOBAL'
tx.noise_basis = 'BLENDER_ORIGINAL'
for p in wme.polygons: p.use_smooth = True
wm_, wnt, wb = new_mat('water')
wb.inputs['Base Color'].default_value = (*mixc((0.88, 0.98, 0.95), (0.4, 0.45, 0.6), M), 1)
wb.inputs['Transmission Weight'].default_value = 1.0
wb.inputs['IOR'].default_value = 1.333
wb.inputs['Roughness'].default_value = 0.035
vol = wnt.nodes.new('ShaderNodeVolumeAbsorption')
vol.inputs['Color'].default_value = (*mixc((0.32, 0.8, 0.68), (0.15, 0.2, 0.32), M), 1)
vol.inputs['Density'].default_value = lerp(0.09, 0.6, M)
wnt.links.new(vol.outputs['Volume'], wnt.nodes['Material Output'].inputs['Volume'])
water.data.materials.append(wm_)
if os.environ.get('NOWATER'): water.hide_render = True

# ---------------------------------------------------------------- smoke from the pyres
for k, sm in enumerate(info['smokes']):
    p, spread, height = sm['p'], sm['spread'], sm['height']
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    ob = bpy.context.active_object; ob.name = f'smoke_{k}'
    ob.scale = (0.4 * spread + 0.2, 0.4 * spread + 0.2, height * 0.55)
    ob.location = T((p[0] + 0.55 * spread, p[1] + height * 0.5, p[2] - 0.2 * spread))
    ob.rotation_euler = (0, math.radians(18), 0)
    m, nt, bsdf = new_mat(f'smoke_{k}'); nt.nodes.remove(bsdf)
    pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (0.72, 0.7, 0.68, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord'); ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], ln.inputs[0])
    fall = nt.nodes.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 1.0; fall.inputs['From Max'].default_value = 0.2
    nt.links.new(ln.outputs['Value'], fall.inputs['Value'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 6
    nz.noise_dimensions = '4D'; nz.inputs['W'].default_value = T_SEC * 0.3 + k
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[1].position = 0.75
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(fall.outputs['Result'], mul.inputs[0]); nt.links.new(ramp.outputs['Color'], mul.inputs[1])
    dens = nt.nodes.new('ShaderNodeMath'); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.9
    nt.links.new(mul.outputs['Value'], dens.inputs[0]); nt.links.new(dens.outputs['Value'], pv.inputs['Density'])
    nt.links.new(pv.outputs['Volume'], nt.nodes['Material Output'].inputs['Volume'])
    ob.data.materials.append(m)


# fire: hide the cone flames and grow a glowing volume above each pyre
for ob in list(scene.objects):
    if ob.type == 'MESH' and any(sl.material and sl.material.name.startswith('flame') for sl in ob.material_slots):
        ob.hide_render = True
fire_mat, fnt, fb = new_mat('fire'); fnt.nodes.remove(fb)
fv = fnt.nodes.new('ShaderNodeVolumePrincipled'); fv.inputs['Density'].default_value = 0.0
fv.inputs['Emission Color'].default_value = (1.0, 0.42, 0.08, 1)
ftc = fnt.nodes.new('ShaderNodeTexCoord'); fsep = fnt.nodes.new('ShaderNodeSeparateXYZ'); fnt.links.new(ftc.outputs['Object'], fsep.inputs['Vector'])
flen = fnt.nodes.new('ShaderNodeVectorMath'); flen.operation = 'LENGTH'; fnt.links.new(ftc.outputs['Object'], flen.inputs[0])
fcore = fnt.nodes.new('ShaderNodeMapRange'); fcore.inputs['From Min'].default_value = 1.0; fcore.inputs['From Max'].default_value = 0.0
fnt.links.new(flen.outputs['Value'], fcore.inputs['Value'])
fnz = fnt.nodes.new('ShaderNodeTexNoise'); fnz.noise_dimensions = '4D'; fnz.inputs['W'].default_value = T_SEC * 2.0
fnz.inputs['Scale'].default_value = 3.0; fnz.inputs['Detail'].default_value = 5
fmp = fnt.nodes.new('ShaderNodeMapping'); fmp.inputs['Scale'].default_value = (1, 1, 0.5); fnt.links.new(ftc.outputs['Object'], fmp.inputs['Vector'])
fnt.links.new(fmp.outputs['Vector'], fnz.inputs['Vector'])
fr = fnt.nodes.new('ShaderNodeValToRGB'); fr.color_ramp.elements[0].position = 0.45; fr.color_ramp.elements[1].position = 0.7
fnt.links.new(fnz.outputs['Fac'], fr.inputs['Fac'])
fm1 = fnt.nodes.new('ShaderNodeMath'); fm1.operation = 'MULTIPLY'; fnt.links.new(fcore.outputs['Result'], fm1.inputs[0]); fnt.links.new(fr.outputs['Color'], fm1.inputs[1])
fm2 = fnt.nodes.new('ShaderNodeMath'); fm2.operation = 'MULTIPLY'; fm2.inputs[1].default_value = lerp(28, 45, M)
fnt.links.new(fm1.outputs['Value'], fm2.inputs[0]); fnt.links.new(fm2.outputs['Value'], fv.inputs['Emission Strength'])
fnt.links.new(fv.outputs['Volume'], fnt.nodes['Material Output'].inputs['Volume'])
for i, f in enumerate(info['fires']):
    base = T(f) + Vector((0, 0, -0.32))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=base)
    ob = bpy.context.active_object; ob.name = f'fire_vol_{i}'; ob.scale = (0.2, 0.2, 0.36)
    ob.data.materials.append(fire_mat)
# ---------------------------------------------------------------- lights
def point(name, loc, color, watts, radius=0.1):
    ld = bpy.data.lights.new(name, 'POINT'); ld.color = color; ld.energy = watts; ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld); ob.location = loc; scene.collection.objects.link(ob); return ob

for i, f in enumerate(info['fires']):
    point(f'fire_{i}', T(f), (1.0, 0.5, 0.2), lerp(60, 160, M), 0.18)
if M > 0.02:
    flame = emissive('lamp_flame', (1.0, 0.62, 0.22), 60 * M)
    for i, (x, y, z) in enumerate(info['aarti']):
        r = 0.1 * M; ph = T_SEC * 2.0
        c = T((x + r * math.cos(ph), y + r * math.sin(ph) + 0.11, z))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=c); bpy.context.active_object.data.materials.append(flame)
        point(f'aarti_{i}', c + Vector((0, -0.05, 0.05)), (1.0, 0.6, 0.25), 70 * M, 0.05)
    diya = emissive('diya', (1.0, 0.55, 0.18), 80 * M)
    cup = plain('diya_cup', (0.35, 0.2, 0.08), 0.8)
    for x0, z, spd in info['diyas']:
        x = ((x0 + spd * T_SEC + 11.7) % 23.4) - 11.7
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.02, vertices=10, location=T((x, 0.03, z)))
        bpy.context.active_object.data.materials.append(cup)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.018, location=T((x, 0.07, z)), segments=10, ring_count=6)
        bpy.context.active_object.data.materials.append(diya)

sun_dir = T(mixc((-8, 11, 15), (-11, 9, -14), M)).normalized()
sd = bpy.data.lights.new('sun', 'SUN'); sd.energy = lerp(4.2, 0.5, M); sd.angle = math.radians(3)
sd.color = mixc((1.0, 0.8, 0.6), (1.0, 0.42, 0.28), M)
sun = bpy.data.objects.new('sun', sd); scene.collection.objects.link(sun)
sun.rotation_euler = sun_dir.to_track_quat('Z', 'Y').to_euler()

# world: soft sky fill for lighting, a studio sweep colour for the camera
world = bpy.data.worlds.new('world'); scene.world = world; world.use_nodes = True
wn = world.node_tree; wn.nodes.clear()
wo = wn.nodes.new('ShaderNodeOutputWorld')
sky = wn.nodes.new('ShaderNodeBackground'); sky.inputs['Color'].default_value = (*mixc((0.75, 0.78, 0.88), (0.14, 0.11, 0.3), M), 1)
sky.inputs['Strength'].default_value = lerp(1.0, 0.9, M)
sweep = wn.nodes.new('ShaderNodeBackground')
sweep.inputs['Color'].default_value = (*mixc((0.98, 0.86, 0.68), (0.09, 0.05, 0.16), M), 1); sweep.inputs['Strength'].default_value = 1.15
lp = wn.nodes.new('ShaderNodeLightPath'); mixw = wn.nodes.new('ShaderNodeMixShader')
wn.links.new(lp.outputs['Is Camera Ray'], mixw.inputs['Fac'])
wn.links.new(sky.outputs['Background'], mixw.inputs[1]); wn.links.new(sweep.outputs['Background'], mixw.inputs[2])
wn.links.new(mixw.outputs['Shader'], wo.inputs['Surface'])

# floor under the diorama, same colour as the sweep, catching its shadow
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -3.705))
floor = bpy.context.active_object; floor.name = 'floor'
floor.data.materials.append(plain('floor', mixc((0.9, 0.78, 0.6), (0.06, 0.035, 0.1), M), 0.9))

# ---------------------------------------------------------------- camera (same keys and curve as the video)
KEYS = [(0, (15.6, 1.7, 11.2), (9.6, 1.7, 1.6)), (5, (9.4, 2.1, 8.2), (6.6, 1.4, 0.2)),
        (10, (3.2, 2.0, 7.0), (1.75, 2.6, -3.2)), (14, (2.3, 6.2, 2.6), (1.75, 5.3, -7.2)),
        (18, (-0.5, 9.5, 10.5), (-1.2, 2.2, -2.6)), (23, (-1.2, 5.6, 11.0), (-4.0, 1.2, -0.4)),
        (27, (-1.8, 4.1, 9.6), (-4.0, 1.0, 0.0)), (30, (-2.3, 3.4, 8.2), (-4.0, 0.9, 0.1))]
def cr(p0, p1, p2, p3, s):
    s2, s3 = s * s, s * s * s
    return tuple(0.5 * ((2 * b) + (-a + c) * s + (2 * a - 5 * b + 4 * c - d) * s2 + (-a + 3 * b - 3 * c + d) * s3)
                 for a, b, c, d in zip(p0, p1, p2, p3))
def camera_at(t):
    i = 0
    while i < len(KEYS) - 2 and t >= KEYS[i + 1][0]: i += 1
    a, b, c, d = KEYS[max(0, i - 1)], KEYS[i], KEYS[i + 1], KEYS[min(len(KEYS) - 1, i + 2)]
    s = min(1, max(0, (t - b[0]) / (c[0] - b[0])))
    if i == len(KEYS) - 2: s = 1 - (1 - s) ** 3
    return cr(a[1], b[1], c[1], d[1], s), cr(a[2], b[2], c[2], d[2], s)
cp, cq = camera_at(T_SEC)
cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); scene.collection.objects.link(cam)
cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(36); cd.clip_start = 0.1; cd.clip_end = 200
cam.location = T(cp); cam.rotation_euler = (T(cq) - T(cp)).to_track_quat('-Z', 'Y').to_euler()
cd.dof.use_dof = True; cd.dof.focus_distance = (T(cq) - T(cp)).length; cd.dof.aperture_fstop = 0.9
scene.camera = cam

# ---------------------------------------------------------------- render settings
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print('GPU setup failed, using CPU:', e)
scene.cycles.samples = SAMPLES; scene.cycles.use_adaptive_sampling = True; scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8; scene.cycles.transmission_bounces = 8; scene.cycles.volume_bounces = 1
scene.cycles.caustics_reflective = False; scene.cycles.caustics_refractive = True; scene.cycles.blur_glossy = 1.0
scene.render.resolution_x = 1080; scene.render.resolution_y = 1920; scene.render.resolution_percentage = SCALE
scene.view_settings.view_transform = 'AgX'
for look in ('AgX - Punchy', 'Punchy'):
    try: scene.view_settings.look = look; break
    except Exception: pass
scene.view_settings.exposure = lerp(0.45, 1.3, M)
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if SAVE:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, SAVE))
if os.environ.get('CLAY'):
    clay = plain('clay', (0.7, 0.7, 0.7), 0.8); scene.view_layers[0].material_override = clay
bpy.ops.render.render(write_still=True)
print('RENDERED', OUT)
