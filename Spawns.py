"""Modulo para seleccionar el punto de aparicion (spawn) en el edificio.
Permite elegir un piso y selecciona un salon al azar de ese piso.
"""
import random
import tkinter as tk

# Altura de los ojos del jugador
ALTURA_OJOS = 1.70

# Lista de salones por cada piso: (nombre, x, y, z)
# La coordenada Y corresponde a la altura del suelo mas la altura de los ojos
SALONES_POR_PISO = {
    1: [
        ("Aula 101", 1.50, 0.11 + ALTURA_OJOS, -2.00),
        ("Aula 102", 10.50, 0.11 + ALTURA_OJOS, -2.00),
        ("Aula 103", 19.50, 0.11 + ALTURA_OJOS, -2.00),
    ],
    2: [
        ("Aula 201", 1.50, 3.71 + ALTURA_OJOS, -2.00),
        ("Aula 202", 10.50, 3.71 + ALTURA_OJOS, -2.00),
        ("Aula 203", 19.50, 3.71 + ALTURA_OJOS, -2.00),
    ],
    3: [
        ("Aula 301", 1.50, 7.31 + ALTURA_OJOS, -2.00),
        ("Aula 302", 10.50, 7.31 + ALTURA_OJOS, -2.00),
        ("Aula 303", 19.50, 7.31 + ALTURA_OJOS, -2.00),
    ],
    4: [
        ("Aula 401", 1.50, 10.91 + ALTURA_OJOS, -2.00),
        ("Aula 402", 10.50, 10.91 + ALTURA_OJOS, -2.00),
        ("Aula 403", 19.50, 10.91 + ALTURA_OJOS, -2.00),
    ],
}


def obtener_spawn_piso(piso):
    """Elige un salon al azar dentro del piso indicado."""
    if piso not in SALONES_POR_PISO:
        piso = 1

    salones = SALONES_POR_PISO[piso]
    nombre_salon, x, y, z = random.choice(salones)

    posicion = (x, y, z)
    yaw = 0.0      # Orientacion horizontal de la camara
    pitch = -2.0   # Inclinacion vertical de la camara

    info = {
        "piso": f"Piso {piso}",
        "piso_nombre": f"Piso {piso}",
        "aula": nombre_salon,
        "descripcion": f"{nombre_salon} (Piso {piso})"
    }
    return posicion, yaw, pitch, info


def mostrar_menu_spawns():
    """Muestra un menu simple para elegir el piso."""
    resultado = [None]

    def al_elegir_piso(piso):
        resultado[0] = obtener_spawn_piso(piso)
        ventana.destroy()

    def al_cerrar():
        # Si se cierra la ventana con la X, se usa el piso 1 por defecto
        if resultado[0] is None:
            resultado[0] = obtener_spawn_piso(1)
        ventana.destroy()

    # Creacion de la ventana de seleccion
    ventana = tk.Tk()
    ventana.title("Seleccionar Piso")
    ventana.resizable(False, False)
    ventana.configure(bg="#181a24")

    # Tamano y centrado de la ventana
    ancho = 480
    alto = 360
    pantalla_x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    pantalla_y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{pantalla_x}+{pantalla_y}")

    # Asegurar que la ventana quede al frente
    ventana.lift()
    ventana.attributes("-topmost", True)
    ventana.after_idle(ventana.attributes, "-topmost", False)
    ventana.protocol("WM_DELETE_WINDOW", al_cerrar)

    # Titulo superior (sin emojis)
    panel_titulo = tk.Frame(ventana, bg="#202336", pady=16)
    panel_titulo.pack(fill="x")

    etiqueta_titulo = tk.Label(
        panel_titulo,
        text="SIMULADOR DE DESASTRE 3D",
        font=("Segoe UI", 14, "bold"),
        fg="#ffffff",
        bg="#202336"
    )
    etiqueta_titulo.pack()

    etiqueta_subtitulo = tk.Label(
        panel_titulo,
        text="Pabellon Universitario - Elige tu punto de aparicion",
        font=("Segoe UI", 9),
        fg="#94a3b8",
        bg="#202336"
    )
    etiqueta_subtitulo.pack(pady=(2, 0))

    # Panel con los botones de cada piso
    panel_botones = tk.Frame(ventana, bg="#181a24", padx=24, pady=18)
    panel_botones.pack(fill="both", expand=True)

    # Informacion de cada boton: numero de piso, texto y colores
    opciones = [
        (1, "PISO 1  —  Aulas 101, 102 y 103 (Nivel Terreno)", "#2563eb", "#1d4ed8"),
        (2, "PISO 2  —  Aulas 201, 202 y 203 (Segundo Nivel)", "#0284c7", "#0369a1"),
        (3, "PISO 3  —  Aulas 301, 302 y 303 (Tercer Nivel)", "#0d9488", "#0f766e"),
        (4, "PISO 4  —  Aulas 401, 402 y 403 (Cuarto Nivel)", "#7c3aed", "#6d28d9"),
    ]

    for piso_num, texto, color_normal, color_hover in opciones:
        boton = tk.Button(
            panel_botones,
            text=texto,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=color_normal,
            activebackground=color_hover,
            activeforeground="#ffffff",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=lambda p=piso_num: al_elegir_piso(p)
        )
        boton.pack(fill="x", pady=6)

        # Efecto de cambio de color al pasar el cursor
        boton.bind("<Enter>", lambda e, b=boton, c=color_hover: b.config(bg=c))
        boton.bind("<Leave>", lambda e, b=boton, c=color_normal: b.config(bg=c))

    # Iniciar la interfaz grafica
    ventana.mainloop()

    # Si no hubo seleccion, usar piso 1 por defecto
    if resultado[0] is None:
        return obtener_spawn_piso(1)

    return resultado[0]


if __name__ == "__main__":
    # Si se ejecuta este archivo directamente, se inicia el simulador
    import main
    main.main()
