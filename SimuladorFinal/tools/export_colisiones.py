
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

# Obtener la ruta de salida
out = Path(sys.argv[sys.argv.index("--") + 1])

# Objetos que queremos convertir en obstáculos
TIPOS_OBSTACULO = (
    "muro",
    "pared",
    "pilar",
    "columna",
    "alfeizar",
    "alféizar",
    "baranda",
    "pasamanos"
    )

cajas = []
nombres = []

for obj in bpy.data.objects:

    # Solo procesar objetos con geometría
    if obj.type != "MESH" or obj.hide_render:
        continue

    nombre = obj.name.lower()

    # Filtrar por nombres
    if not any(tipo in nombre for tipo in TIPOS_OBSTACULO):
        continue

    # Obtener las 8 esquinas del objeto en el mundo
    esquinas = [
        obj.matrix_world @ Vector(esquina)
        for esquina in obj.bound_box
    ]

    # Convertir coordenadas Blender -> OpenGL
    # Blender: X, Y, Z
    # OpenGL:  X, Z, -Y
    puntos = np.array([
        [p.x, p.z, -p.y]
        for p in esquinas
    ], dtype=np.float32)

    minimo = puntos.min(axis=0)
    maximo = puntos.max(axis=0)

    # Ignorar geometría degenerada
    if np.any(maximo - minimo < 0.001):
        continue

    cajas.append([
        minimo[0], minimo[1], minimo[2],
        maximo[0], maximo[1], maximo[2]
    ])

    nombres.append(obj.name)

# Convertir a arreglos NumPy
cajas = np.array(cajas, dtype=np.float32).reshape(-1, 6)
nombres = np.array(nombres, dtype=str)

# Crear la carpeta si no existe
out.parent.mkdir(parents=True, exist_ok=True)

# Guardar resultados
np.savez_compressed(
    out,
    boxes=cajas,
    names=nombres
)

print("COLISIONES EXPORTADAS:", len(cajas))
print("Archivo generado:", out)

for nombre in nombres[:10]:
    print(" -", nombre)
