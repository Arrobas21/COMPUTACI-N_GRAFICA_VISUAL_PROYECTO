"""Simulador de desastre 3D - escenario del Pabellon Universitario (OpenGL 3.3 core).
Controles: WASD mover, mouse mirar, SHIFT correr, F1 wireframe, ESC salir. Suelo, escaleras y gravedad."""
import ctypes
import math
import os
import struct
import sys
import zlib
from pathlib import Path

import glfw
import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_COMPILE_STATUS,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FALSE,
    GL_FILL,
    GL_FLOAT,
    GL_FRAGMENT_SHADER,
    GL_FRONT_AND_BACK,
    GL_LINE,
    GL_LINK_STATUS,
    GL_MULTISAMPLE,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_RGB,
    GL_SRC_ALPHA,
    GL_STATIC_DRAW,
    GL_TRIANGLES,   
    GL_TRUE,
    GL_UNSIGNED_BYTE,
    GL_VERTEX_SHADER,
    glAttachShader,
    glBindBuffer,
    glBindVertexArray,
    glBlendFunc,
    glBufferData,
    glClear,
    glClearColor,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDepthMask,
    glDisable,
    glDrawArrays,
    glEnable,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glPolygonMode,
    glReadPixels,
    glShaderSource,
    glUniform1f,
    glUniform3fv,
    glUniform4fv,
    glUniformMatrix4fv,
    glUseProgram,
    glVertexAttribPointer,
    glViewport,
)  # noqa: F401

ASSETS = Path(__file__).parent / "assets" / "pabellon_final.npz"
COLISIONES_ASSETS = (
    Path(__file__).parent / "assets" / "colisiones_final.npz"
)

SUELOS_ASSETS = Path(__file__).parent / "assets" / "suelos_final.npz"
ALTURA_OJOS = 1.70
ALTURA_PERSONA = 1.70
RADIO_PERSONA = 0.30
ALTURA_ESCALON = 0.32        # Altura máxima que sube en un paso
GRAVEDAD = 17.0              # Unidades/s²
VELOCIDAD_CAIDA_MAX = 25.0
SUELO_EXTERIOR = -0.10        # Coincide con make_ground()

VS = """#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
uniform mat4 uVP;
out vec3 vN; out vec3 vP;
void main(){ vN = aNormal; vP = aPos; gl_Position = uVP * vec4(aPos, 1.0); }
"""
FS = """#version 330 core
in vec3 vN; in vec3 vP;
uniform vec4 uColor; uniform float uEmit; uniform vec3 uSun; uniform vec3 uEye;
out vec4 FragColor;
void main(){
    vec3 n = normalize(vN);
    if(!gl_FrontFacing) n = -n;
    float diff = max(dot(n, uSun), 0.0);
    float hemi = 0.5 + 0.5 * n.y;
    vec3 amb = mix(vec3(0.30, 0.28, 0.26), vec3(0.45, 0.52, 0.62), hemi);
    vec3 col = uColor.rgb * (amb + vec3(1.0, 0.95, 0.85) * diff * 0.85);
    col = mix(col, uColor.rgb, uEmit);
    float d = length(vP - uEye);
    col = mix(col, vec3(0.62, 0.74, 0.88), clamp((d - 80.0) / 220.0, 0.0, 0.85));
    FragColor = vec4(col, uColor.a);
}
"""


def compile_program():
    def sh(kind, src):
        s = glCreateShader(kind)
        glShaderSource(s, src)
        glCompileShader(s)
        if not glGetShaderiv(s, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(s).decode())
        return s
    p = glCreateProgram()
    glAttachShader(p, sh(GL_VERTEX_SHADER, VS))
    glAttachShader(p, sh(GL_FRAGMENT_SHADER, FS))
    glLinkProgram(p)
    if not glGetProgramiv(p, GL_LINK_STATUS):
        raise RuntimeError(glGetProgramInfoLog(p).decode())
    return p


class Mesh:
    def __init__(self, verts, color, emit):
        self.count = len(verts)
        self.color, self.emit = color, emit
        self.vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(12))

    def draw(self):
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.count)


def load_scene():
    data = np.load(ASSETS)
    opaque, glass = [], []
    for k in data.files:
        if k.startswith("_c_"):
            continue
        c = data["_c_" + k]
        m = Mesh(np.ascontiguousarray(data[k]), c[:4], c[4])
        (glass if c[3] < 0.99 else opaque).append(m)
    return opaque, glass


def make_ground(size=400.0):
    y = -0.1
    v = [(-size, y, -size), (-size, y, size), (size, y, size), (-size, y, -size), (size, y, size), (size, y, -size)]
    arr = np.array([[*p, 0, 1, 0] for p in v], np.float32)
    return Mesh(arr, np.array([0.33, 0.50, 0.28, 1.0], np.float32), 0.0)


def perspective(fov, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov) / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def look_dir(eye, d):
    f = d / np.linalg.norm(d)
    s = np.cross(f, [0, 1, 0]); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4, np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[0, 3], m[1, 3], m[2, 3] = -s @ eye, -u @ eye, f @ eye
    return m


def save_png(path, w, h):
    raw = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
    rows = np.frombuffer(raw, np.uint8).reshape(h, w * 3)[::-1]
    data = b"".join(b"\x00" + r.tobytes() for r in rows)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b""))

def cargar_colisiones():
    with np.load(COLISIONES_ASSETS) as datos:
        cajas = datos["boxes"].copy()

    print("Obstáculos cargados:", len(cajas))
    return cajas


def hay_colision(posicion, cajas, radio=0.30):
    x, y, z = posicion

    pies = y - 1.60
    cabeza = y + 0.10

    # 1. Filtrar obstáculos por altura
    filtro_y = (
        (cajas[:, 1] < cabeza) &
        (cajas[:, 4] > pies)
    )

    # 2. Descartar cajas demasiado alejadas
    filtro_x = (
        (cajas[:, 0] < x + radio) &
        (cajas[:, 3] > x - radio)
    )

    filtro_z = (
        (cajas[:, 2] < z + radio) &
        (cajas[:, 5] > z - radio)
    )

    cercanas = cajas[filtro_y & filtro_x & filtro_z]

    if len(cercanas) == 0:
        return False

    # 3. Calcular distancias a las cajas cercanas
    cerca_x = np.clip(
        x, cercanas[:, 0], cercanas[:, 3]
    )

    cerca_z = np.clip(
        z, cercanas[:, 2], cercanas[:, 5]
    )

    dx = x - cerca_x
    dz = z - cerca_z

    # 4. Comprobar si alguna caja colisiona
    return bool(np.any(
        dx * dx + dz * dz < radio * radio
    ))



def cargar_suelos():
    """Lee triángulos exportados de Blender: forma (N,3,3), Y hacia arriba."""
    with np.load(SUELOS_ASSETS) as datos:
        tri = np.asarray(datos["triangles"], dtype=np.float32)
    if tri.ndim != 3 or tri.shape[1:] != (3, 3):
        raise ValueError("suelos_final.npz necesita triangles con forma (N, 3, 3)")
    print("Triángulos de suelo cargados:", len(tri))
    return tri


def altura_superficie(x, z, pies, triangulos, paso_max=ALTURA_ESCALON):
    """Altura alcanzable más alta bajo x,z, sin saltar entre niveles.

    Usa coordenadas baricéntricas para hallar la altura sobre cada triángulo.
    No selecciona suelos más altos que los pies + paso_max.
    """
    mejor = None
    for tri in triangulos:
        a, b, c = tri
        # Rechazo rápido por límites 2D.
        if not (min(a[0], b[0], c[0]) - 1e-5 <= x <= max(a[0], b[0], c[0]) + 1e-5):
            continue
        if not (min(a[2], b[2], c[2]) - 1e-5 <= z <= max(a[2], b[2], c[2]) + 1e-5):
            continue
        den = ((b[2] - c[2]) * (a[0] - c[0])
               + (c[0] - b[0]) * (a[2] - c[2]))
        if abs(float(den)) < 1e-8:
            continue
        u = ((b[2] - c[2]) * (x - c[0])
             + (c[0] - b[0]) * (z - c[2])) / den
        v = ((c[2] - a[2]) * (x - c[0])
             + (a[0] - c[0]) * (z - c[2])) / den
        w = 1.0 - u - v
        if min(u, v, w) < -1e-5:
            continue
        alto = float(u * a[1] + v * b[1] + w * c[1])
        if alto <= pies + paso_max + 1e-4 and (mejor is None or alto > mejor):
            mejor = alto

    # La plataforma verde exterior dibujada con make_ground() está a -0.1.
    # Solo es un soporte de emergencia si no hay suelo exportado encima.
    if mejor is None and pies >= SUELO_EXTERIOR - paso_max:
        mejor = SUELO_EXTERIOR
    return mejor


def main():
    if not glfw.init():
        sys.exit("No se pudo iniciar GLFW")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.SAMPLES, 4)

    win = glfw.create_window(
        1280, 720,
        "Simulador Desastre 3D - Pabellon",
        None, None
    )

    if not win:
        glfw.terminate()
        sys.exit("No se pudo crear la ventana OpenGL 3.3")

    glfw.make_context_current(win)
    glfw.swap_interval(1)
    glfw.set_input_mode(win, glfw.CURSOR, glfw.CURSOR_DISABLED)

    # Preparar el escenario
    prog = compile_program()
    opaque, glass = load_scene()
    ground = make_ground()
    colisiones = cargar_colisiones()
    suelos = cargar_suelos()

    loc = {
        n: glGetUniformLocation(prog, n)
        for n in ("uVP", "uColor", "uEmit", "uSun", "uEye")
    }

    sun = np.array([0.4, 0.8, 0.45], np.float32)
    sun /= np.linalg.norm(sun)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_MULTISAMPLE)
    glClearColor(0.62, 0.74, 0.88, 1)

    # Posición inicial del jugador
    eye = np.array([0.0, 1.7, 26.0], np.float32)

    # Empezar con los pies sobre el terreno exterior.
    eye[1] = SUELO_EXTERIOR + ALTURA_OJOS
    velocidad_y = 0.0
    yaw = -90.0
    pitch = -2.0

    shot = os.environ.get("SHOT")

    if shot:
        shot, pos, yaw, pitch = shot.split(";")
        eye = np.array(
            [float(c) for c in pos.split(",")],
            np.float32
        )
        yaw, pitch = float(yaw), float(pitch)

    frames = 0
    last = glfw.get_time()

    mx = None
    my = None

    wire = False
    f1_prev = False

    # Bucle principal del simulador
    while (
        not glfw.window_should_close(win)
        and glfw.get_key(win, glfw.KEY_ESCAPE) != glfw.PRESS
    ):

        now = glfw.get_time()
        dt = min(now - last, 0.1)
        last = now

        glfw.poll_events()

        # ---------------------------------
        # 1. MOVIMIENTO DE LA CÁMARA
        # ---------------------------------

        x, y = glfw.get_cursor_pos(win)

        if mx is not None and not shot:
            yaw += (x - mx) * 0.1
            pitch = max(
                -89.0,
                min(89.0, pitch - (y - my) * 0.1)
            )

        mx, my = x, y

        fwd = np.array([
            math.cos(math.radians(yaw))
            * math.cos(math.radians(pitch)),

            math.sin(math.radians(pitch)),

            math.sin(math.radians(yaw))
            * math.cos(math.radians(pitch))
        ], np.float32)

        flat = np.array(
            [fwd[0], 0, fwd[2]],
            np.float32
        )

        flat /= np.linalg.norm(flat)

        right = np.cross(
            flat, [0, 1, 0]
        ).astype(np.float32)

        # ---------------------------------
        # 2. CONTROLES DEL JUGADOR
        # ---------------------------------

        k = lambda key: (
            glfw.get_key(win, key) == glfw.PRESS
        )

        v = np.zeros(3, np.float32)

        if k(glfw.KEY_W):
            v += flat

        if k(glfw.KEY_S):
            v -= flat

        if k(glfw.KEY_D):
            v += right

        if k(glfw.KEY_A):
            v -= right

        # ---------------------------------
        # 3. VELOCIDAD DEL JUGADOR
        # ---------------------------------

        speed = (
            9.0 if k(glfw.KEY_LEFT_SHIFT)
            else 4.0
        )

        # Evitar mayor velocidad diagonal
        magnitud = np.linalg.norm(v)

        if magnitud > 1.0:
            v /= magnitud

        movimiento = v * speed * dt

        # Movimiento fraccionado, con resolución independiente por eje.
        # Una subida de escalón solo se autoriza si la altura está cerca
        # del suelo actual y no se invade una caja de colisión.
        distancia = max(abs(float(movimiento[0])), abs(float(movimiento[2])))
        pasos = max(1, math.ceil(distancia / 0.07))
        paso = movimiento / pasos

        for _ in range(pasos):
            for eje in (0, 2):
                candidato = eye.copy()
                candidato[eje] += paso[eje]

                pies_actuales = float(eye[1] - ALTURA_OJOS)
                suelo_nuevo = altura_superficie(
                    float(candidato[0]), float(candidato[2]),
                    pies_actuales, suelos, paso_max=1.0
                )

                # Un escalón demasiado alto es un obstáculo, no un teletransporte.
                if (suelo_nuevo is not None
                        and suelo_nuevo - pies_actuales > ALTURA_ESCALON + 1e-4):
                    continue
                if suelo_nuevo is not None and suelo_nuevo > pies_actuales:
                    candidato[1] = suelo_nuevo + ALTURA_OJOS
                # Prohibir colisiones usando altura que tendría el jugador.
                if not hay_colision(candidato, colisiones):
                    eye[:] = candidato
                    if suelo_nuevo is not None and suelo_nuevo >= pies_actuales:
                        velocidad_y = 0.0

        # Física vertical: apoyar los pies si hay suelo bajo ellos;
        # de lo contrario aplicar caída sin atravesar la plataforma.
        pies_actuales = float(eye[1] - ALTURA_OJOS)
        suelo = altura_superficie(
            float(eye[0]), float(eye[2]), pies_actuales, suelos
        )
        if suelo is not None and pies_actuales <= suelo + 0.015 and velocidad_y <= 0:
            eye[1] = suelo + ALTURA_OJOS
            velocidad_y = 0.0
        else:
            velocidad_y = max(velocidad_y - GRAVEDAD * dt, -VELOCIDAD_CAIDA_MAX)
            pies_siguientes = pies_actuales + velocidad_y * dt
            if suelo is not None and pies_siguientes <= suelo:
                eye[1] = suelo + ALTURA_OJOS
                velocidad_y = 0.0
            else:
                eye[1] = pies_siguientes + ALTURA_OJOS

        # ---------------------------------
        # 5. MODO WIREFRAME
        # ---------------------------------

        f1 = k(glfw.KEY_F1)

        if f1 and not f1_prev:
            wire = not wire

        f1_prev = f1

        # ---------------------------------
        # 6. CONFIGURACIÓN DEL RENDERIZADO
        # ---------------------------------

        w, h = glfw.get_framebuffer_size(win)

        glViewport(0, 0, w, max(h, 1))

        glClear(
            GL_COLOR_BUFFER_BIT |
            GL_DEPTH_BUFFER_BIT
        )

        glPolygonMode(
            GL_FRONT_AND_BACK,
            GL_LINE if wire else GL_FILL
        )

        vp = (
            perspective(
                70,
                w / max(h, 1),
                0.1,
                600
            )
            @ look_dir(eye, fwd)
        )

        glUseProgram(prog)

        glUniformMatrix4fv(
            loc["uVP"], 1, GL_TRUE, vp
        )

        glUniform3fv(
            loc["uSun"], 1, sun
        )

        glUniform3fv(
            loc["uEye"], 1, eye
        )

        # ---------------------------------
        # 7. DIBUJAR LOS OBJETOS
        # ---------------------------------

        def draw(m):
            glUniform4fv(
                loc["uColor"], 1, m.color
            )

            glUniform1f(
                loc["uEmit"], m.emit
            )

            m.draw()

        draw(ground)

        # Objetos opacos
        for m in opaque:
            draw(m)

        # Objetos transparentes
        glEnable(GL_BLEND)

        glBlendFunc(
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA
        )

        glDepthMask(GL_FALSE)

        for m in glass:
            draw(m)

        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)

        glfw.swap_buffers(win)

        frames += 1

        # Captura automática opcional
        if shot and frames == 3:
            save_png(shot, w, h)
            break

    glfw.terminate()



if __name__ == "__main__":
    main()
