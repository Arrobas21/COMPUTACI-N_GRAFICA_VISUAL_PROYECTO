"""Ejecutar con Blender:  blender -b pabellon.blend --python tools/export_blend.py -- salida.npz
Exporta toda la geometria en espacio mundo (Y arriba), agrupada por material."""
import sys
import bpy
import numpy as np
from mathutils import Matrix

out = sys.argv[sys.argv.index("--") + 1]
# Blender: Z arriba -> OpenGL: Y arriba
to_gl = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
to_gl3 = to_gl.to_3x3()

groups = {}  # material -> [array Nx6 (pos, normal)]
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.hide_render:
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    if not len(me.loop_triangles):
        ev.to_mesh_clear()
        continue
    mw = to_gl @ ev.matrix_world
    nm = (to_gl3 @ ev.matrix_world.to_3x3()).inverted_safe().transposed()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    pos = (np.array(mw.to_3x3(), np.float32) @ co.T).T + np.array(mw.translation, np.float32)
    cn = np.empty(len(me.corner_normals) * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3)
    cn = (np.array(nm, np.float32) @ cn.T).T
    cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-9)
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tv)
    tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("loops", tl)
    tm = np.empty(nt, np.int32); me.loop_triangles.foreach_get("material_index", tm)
    data = np.hstack([pos[tv], cn[tl]])
    if np.linalg.det(np.array(mw.to_3x3())) < 0:  # espejo: invertir orden
        data = data.reshape(-1, 3, 6)[:, ::-1].reshape(-1, 6)
    mats = list(ev.data.materials)
    for i in np.unique(tm):
        name = mats[i].name if i < len(mats) and mats[i] else "_default"
        sel = np.repeat(tm == i, 3)
        groups.setdefault(name, []).append(data[sel])
    ev.to_mesh_clear()

arrays, meta = {}, []
for name, parts in groups.items():
    m = bpy.data.materials.get(name)
    col = list(m.diffuse_color) if m else [0.8, 0.8, 0.8, 1]
    emit = 0.0
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                col = list(n.inputs["Base Color"].default_value)
                col[3] = n.inputs["Alpha"].default_value
                es = n.inputs["Emission Strength"].default_value
                ec = n.inputs["Emission Color"].default_value
                if es > 0 and (ec[0] + ec[1] + ec[2]) > 0.05:
                    emit = 1.0
    arrays[name] = np.vstack(parts).astype(np.float32)
    arrays["_c_" + name] = np.array(col + [emit], np.float32)
np.savez_compressed(out, **arrays)
print("EXPORT OK", {k: len(v) // 3 for k, v in arrays.items() if not k.startswith("_c_")})
