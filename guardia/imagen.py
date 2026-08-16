"""
Placa de concientización de GuardIA (modelo texto -> imagen).

Cada intento de phishing que recibe una PyME es, en el fondo, material de
capacitación. Este módulo convierte el diagnóstico en una placa lista para
compartir por el grupo interno de mensajería o para imprimir y pegar en la
oficina.

El proceso tiene dos pasos:
    1. Se genera la ilustración con un modelo texto-imagen, pidiéndole
       expresamente que NO escriba texto (los modelos visuales deforman las
       palabras, sobre todo en español).
    2. Se compone la placa final con Pillow: encabezado, título, señales y pie,
       en español y sin errores de tipografía.
"""

import base64
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .prompts import construir_prompt_imagen

# ---------------------------------------------------------------------------
# Modelos de imagen, en orden de preferencia
# ---------------------------------------------------------------------------
# Se prueban de más barato a más caro. Si la cuenta no tiene habilitado el
# primero, la aplicación pasa automáticamente al siguiente en lugar de fallar.
MODELOS_IMAGEN = ["gpt-image-1-mini", "gpt-image-1", "dall-e-3"]

TAMANO_ILUSTRACION = "1024x1024"

# Paleta de la marca, la misma que usa la interfaz.
AZUL = (11, 46, 79)
VERDE = (31, 122, 140)
BLANCO = (255, 255, 255)
GRIS = (90, 104, 118)
COLORES_RIESGO = {
    "alto": (192, 57, 43),
    "medio": (214, 137, 16),
    "bajo": (30, 132, 73),
    "indeterminado": (90, 104, 118),
}

# Posibles ubicaciones de una tipografía TrueType. Se recorren en orden: la
# primera es la que instala packages.txt en Streamlit Cloud, las siguientes
# cubren macOS y Windows para el desarrollo local.
RUTAS_FUENTES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
     "/System/Library/Fonts/Supplemental/Arial.ttf"),
    ("/Library/Fonts/Arial Bold.ttf", "/Library/Fonts/Arial.ttf"),
    ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"),
]


class ErrorImagen(Exception):
    """Problema al generar la placa, explicado en español."""


def generar_ilustracion(cliente, tipo_de_engano, nivel_riesgo):
    """Pide la ilustración al modelo texto-imagen.

    Args:
        cliente: instancia de OpenAI.
        tipo_de_engano: técnica detectada en el análisis.
        nivel_riesgo: bajo | medio | alto | indeterminado.

    Returns:
        tuple[Image.Image, str]: la ilustración y el nombre del modelo usado.

    Raises:
        ErrorImagen: si ningún modelo disponible pudo generarla.
    """
    prompt = construir_prompt_imagen(tipo_de_engano, nivel_riesgo)
    ultimo_error = None

    for modelo in MODELOS_IMAGEN:
        try:
            # dall-e-3 devuelve una URL salvo que se pida base64; los modelos
            # gpt-image-1 devuelven base64 siempre y rechazan ese parámetro.
            extra = {"response_format": "b64_json"} if modelo == "dall-e-3" else {}
            respuesta = cliente.images.generate(
                model=modelo,
                prompt=prompt,
                size=TAMANO_ILUSTRACION,
                n=1,
                **extra,
            )
            datos = base64.b64decode(respuesta.data[0].b64_json)
            return Image.open(io.BytesIO(datos)).convert("RGB"), modelo
        except Exception as error:  # noqa: BLE001 - se prueba el siguiente modelo
            ultimo_error = error
            continue

    raise ErrorImagen(
        "No se pudo generar la ilustración con ninguno de los modelos "
        f"disponibles ({', '.join(MODELOS_IMAGEN)}). Detalle: {ultimo_error}"
    )


def _cargar_fuentes():
    """Devuelve una función que entrega la tipografía en el tamaño pedido.

    Recorre las rutas conocidas y usa la primera que exista. Si no encuentra
    ninguna, cae en la tipografía por defecto de Pillow: la placa se genera
    igual, solo que con un tipo más simple.

    Returns:
        callable: fuente(tamaño, negrita=False) -> objeto de fuente de Pillow.
    """
    for ruta_bold, ruta_regular in RUTAS_FUENTES:
        try:
            ImageFont.truetype(ruta_regular, 20)
        except OSError:
            continue

        def fuente(tamano, negrita=False, _b=ruta_bold, _r=ruta_regular):
            try:
                return ImageFont.truetype(_b if negrita else _r, tamano)
            except OSError:
                return ImageFont.truetype(_r, tamano)

        return fuente

    def fuente_por_defecto(tamano, negrita=False):
        return ImageFont.load_default()

    return fuente_por_defecto


def componer_placa(ilustracion, diagnostico):
    """Arma la placa final combinando la ilustración con los textos.

    Los textos se escriben acá y no en el modelo de imagen para que queden en
    español correcto y siempre legibles. El diseño es vertical (1080x1350),
    el formato que mejor se ve en WhatsApp y que también sirve para imprimir.

    Args:
        ilustracion: imagen generada por el modelo texto-imagen.
        diagnostico: diccionario devuelto por `analisis.analizar_mensaje`.

    Returns:
        bytes: la placa final en formato PNG, lista para descargar.
    """
    ancho, alto = 1080, 1350
    alto_encabezado, alto_banda, alto_pie = 130, 520, 100
    margen = 60
    fuente = _cargar_fuentes()

    placa = Image.new("RGB", (ancho, alto), BLANCO)
    lienzo = ImageDraw.Draw(placa)

    nivel = diagnostico.get("nivel_riesgo", "indeterminado")
    color_riesgo = COLORES_RIESGO.get(nivel, GRIS)

    # --- Encabezado -------------------------------------------------------
    lienzo.rectangle([0, 0, ancho, alto_encabezado], fill=AZUL)
    fuente_marca = fuente(46, negrita=True)
    lienzo.text((margen, 32), "Guard", font=fuente_marca, fill=BLANCO)
    lienzo.text(
        (margen + lienzo.textlength("Guard", font=fuente_marca), 32),
        "IA",
        font=fuente_marca,
        fill=(143, 211, 224),
    )
    lienzo.text(
        (margen, 88),
        "Seguridad al alcance de toda la empresa",
        font=fuente(21),
        fill=(168, 200, 214),
    )

    # --- Ilustración ------------------------------------------------------
    # La ilustración llega cuadrada; se recorta la banda central para que ocupe
    # todo el ancho sin deformarse y deje lugar a los textos.
    banda = ImageOps.fit(
        ilustracion, (ancho, alto_banda), method=Image.LANCZOS, centering=(0.5, 0.5)
    )
    placa.paste(banda, (0, alto_encabezado))

    y = alto_encabezado + alto_banda + 42

    # --- Etiqueta de riesgo ----------------------------------------------
    etiqueta = f"RIESGO {nivel.upper()}"
    fuente_etiqueta = fuente(26, negrita=True)
    ancho_etiqueta = lienzo.textlength(etiqueta, font=fuente_etiqueta) + 52
    lienzo.rounded_rectangle(
        [margen, y, margen + ancho_etiqueta, y + 54], radius=27, fill=color_riesgo
    )
    lienzo.text((margen + 26, y + 13), etiqueta, font=fuente_etiqueta, fill=BLANCO)
    y += 84

    # --- Tipo de engaño ---------------------------------------------------
    titulo = diagnostico.get("tipo_de_engano", "Mensaje sospechoso").strip()
    titulo = titulo[:1].upper() + titulo[1:]
    for linea in textwrap.wrap(titulo, width=28)[:2]:
        lienzo.text((margen, y), linea, font=fuente(44, negrita=True), fill=AZUL)
        y += 54
    y += 22

    # --- Señales a reconocer ---------------------------------------------
    lienzo.text(
        (margen, y), "CÓMO RECONOCERLO", font=fuente(21, negrita=True), fill=VERDE
    )
    y += 40

    limite = alto - alto_pie - 30  # nada se dibuja por debajo del pie
    for senal in diagnostico.get("senales", [])[:3]:
        lineas = textwrap.wrap(senal.get("titulo", ""), width=44)[:2]
        if y + 34 * len(lineas) > limite:
            break
        lienzo.ellipse([margen + 4, y + 11, margen + 18, y + 25], fill=VERDE)
        for linea in lineas:
            lienzo.text((margen + 38, y), linea, font=fuente(26), fill=(38, 50, 62))
            y += 34
        y += 12

    # --- Pie --------------------------------------------------------------
    lienzo.rectangle([0, alto - alto_pie, ancho, alto], fill=(240, 244, 247))
    lienzo.text(
        (margen, alto - 70),
        "Ante la duda, verificá por un canal oficial antes de responder.",
        font=fuente(24, negrita=True),
        fill=AZUL,
    )
    lienzo.text(
        (margen, alto - 36),
        "Placa generada con GuardIA · Análisis asistido por IA",
        font=fuente(18),
        fill=GRIS,
    )

    salida = io.BytesIO()
    placa.save(salida, format="PNG")
    return salida.getvalue()


def generar_placa(cliente, diagnostico):
    """Genera la placa completa: ilustración con IA + textos compuestos.

    Args:
        cliente: instancia de OpenAI.
        diagnostico: resultado del análisis texto-texto.

    Returns:
        tuple[bytes, str]: la placa en PNG y el modelo de imagen utilizado.
    """
    ilustracion, modelo = generar_ilustracion(
        cliente,
        diagnostico.get("tipo_de_engano", ""),
        diagnostico.get("nivel_riesgo", "indeterminado"),
    )
    return componer_placa(ilustracion, diagnostico), modelo
