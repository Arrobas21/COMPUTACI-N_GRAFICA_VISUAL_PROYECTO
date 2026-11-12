
import sys
from pathlib import Path

import bpy
import numpy as np

# Ruta de salida
salida = Path(sys.argv[sys.argv.index("--") + 1])

# Nombres de superficies transitables
TIPOS_SUELO = (
    "losa",
    "peldano",
    "peldaño",
    "descanso",
    "piso_pasillo",
    "piso_aula",
    "terreno_plataforma"
)

triangulos = []
nombres = []

depsgraph = bpy.context.evaluated_depsgraph_get()

for obj in bpy.data.objects:

    if obj.type != "MESH" or obj.hide_render:
        continue

    nombre = obj.name.lower()

    if not any(tipo in nombre for tipo in TIPOS_SUELO):
        continue

    evaluado = obj.evaluated_get(depsgraph)
    mesh = evaluado.to_mesh()

    try:
        mesh.calc_loop_triangles()

        matriz = evaluado.matrix_world

        for tri in mesh.loop_triangles:

            # Obtener las tres esquinas del triángulo
            puntos = []

            for indice in tri.vertices:
                p = matriz @ mesh.vertices[indice].co

                # Blender Z arriba -> OpenGL Y arriba
                puntos.append([p.x, p.z, -p.y])

            puntos = np.array(puntos, dtype=np.float32)

            # Calcular normal geométrica
            a = puntos[1] - puntos[0]
            b = puntos[2] - puntos[0]

            normal = np.cross(a, b)
            longitud = np.linalg.norm(normal)

            if longitud < 1e-8:
                continue

            normal /= longitud

            # Solo superficies que miran hacia arriba
            if normal[1] < 0.75:
                continue

            triangulos.append(puntos)
            nombres.append(obj.name)

    finally:
        evaluado.to_mesh_clear()

triangulos = np.array(
    triangulos, dtype=np.float32
).reshape(-1, 3, 3)

nombres = np.array(nombres, dtype=str)

salida.parent.mkdir(parents=True, exist_ok=True)

np.savez_compressed(
    salida,
    triangles=triangulos,
    names=nombres
)

print("EXPORTACION DE SUELOS COMPLETADA")
print("Triangulos transitables:", len(triangulos))
print("Objetos representados:", len(set(nombres)))
print("Archivo:", salida)
