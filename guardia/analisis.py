"""
Motor de análisis de GuardIA (modelo texto -> texto).

Encapsula todo el contacto con la API de OpenAI para el análisis de mensajes:
creación del cliente, llamada con salida dirigida, control de errores y
cálculo del costo real de cada consulta.

La interfaz (app.py) no sabe nada de OpenAI: solo llama a `analizar_mensaje`
y recibe un diccionario ya validado.
"""

import json

from openai import OpenAI

from .prompts import (
    ESQUEMA_DIAGNOSTICO,
    PROMPT_SISTEMA,
    construir_mensaje_usuario,
)

# ---------------------------------------------------------------------------
# Configuración del modelo
# ---------------------------------------------------------------------------
# GPT-4o mini se eligió por su relación entre calidad y precio: es suficiente
# para clasificar señales de phishing en un texto y cuesta una fracción de los
# modelos grandes. Ver "Factibilidad económica" en la documentación.
MODELO_TEXTO = "gpt-4o-mini"

# Precios oficiales de OpenAI en dólares por millón de tokens (agosto 2026).
# Se guardan como constantes para que el costo mostrado en pantalla se calcule
# solo y no quede desactualizado en un texto suelto.
PRECIO_ENTRADA_POR_MILLON = 0.15
PRECIO_SALIDA_POR_MILLON = 0.60

# Temperatura baja: buscamos un diagnóstico estable y reproducible, no
# creatividad. El mismo correo debería recibir siempre una evaluación similar.
TEMPERATURA = 0.2

# Límite defensivo de caracteres del mensaje a analizar. Evita que un pegado
# accidental de un archivo entero dispare un costo innecesario.
MAX_CARACTERES = 12000


class ErrorGuardIA(Exception):
    """Error controlado y explicado en español, listo para mostrar al usuario."""


def crear_cliente(api_key):
    """Crea el cliente de OpenAI.

    Args:
        api_key: clave de la API. Se toma de los secretos de Streamlit o de la
            variable de entorno OPENAI_API_KEY (ver app.py).

    Returns:
        OpenAI: cliente listo para usar.

    Raises:
        ErrorGuardIA: si no hay clave configurada.
    """
    if not api_key:
        raise ErrorGuardIA(
            "No hay una clave de API configurada. Cargá tu clave de OpenAI en "
            "los secretos de la aplicación (OPENAI_API_KEY) para poder analizar "
            "mensajes."
        )
    return OpenAI(api_key=api_key)


def calcular_costo(tokens_entrada, tokens_salida):
    """Calcula el costo en dólares de una consulta, según los tokens usados.

    Args:
        tokens_entrada: tokens del prompt enviado.
        tokens_salida: tokens generados por el modelo.

    Returns:
        float: costo estimado de la consulta en dólares.
    """
    return (
        tokens_entrada * PRECIO_ENTRADA_POR_MILLON
        + tokens_salida * PRECIO_SALIDA_POR_MILLON
    ) / 1_000_000


def _normalizar(diagnostico):
    """Ajusta valores fuera de rango y mantiene la coherencia del resultado.

    Structured Outputs garantiza la estructura del JSON, pero no que el puntaje
    esté dentro de 0-100 ni que sea coherente con el nivel de riesgo. Esta
    función es la última línea de defensa antes de mostrar el resultado.

    Args:
        diagnostico: diccionario devuelto por el modelo.

    Returns:
        dict: el mismo diccionario con los valores saneados.
    """
    puntaje = diagnostico.get("puntaje", 0)
    try:
        puntaje = int(puntaje)
    except (TypeError, ValueError):
        puntaje = 0
    diagnostico["puntaje"] = max(0, min(100, puntaje))

    # Si el nivel y el puntaje se contradicen, mandamos el nivel: es lo que el
    # modelo razonó explícitamente y lo que lee la persona.
    nivel = diagnostico.get("nivel_riesgo", "indeterminado")
    if nivel not in ("bajo", "medio", "alto", "indeterminado"):
        nivel = "indeterminado"
    diagnostico["nivel_riesgo"] = nivel

    diagnostico.setdefault("senales", [])
    return diagnostico


def analizar_mensaje(cliente, cuerpo, remitente="", asunto="", enlaces=""):
    """Analiza un mensaje sospechoso y devuelve el diagnóstico estructurado.

    Es la función principal del proyecto: toma el texto que pegó el usuario,
    lo envía a GPT-4o mini junto con el prompt especializado y devuelve un
    diccionario con la misma forma siempre, gracias a la salida dirigida.

    Args:
        cliente: instancia de OpenAI creada con `crear_cliente`.
        cuerpo: texto del mensaje a analizar.
        remitente: remitente del mensaje (opcional).
        asunto: asunto del mensaje (opcional).
        enlaces: enlaces incluidos en el mensaje (opcional).

    Returns:
        tuple[dict, dict]: (diagnóstico, uso) donde `uso` trae los tokens
        consumidos y el costo de la consulta.

    Raises:
        ErrorGuardIA: ante entrada inválida o cualquier problema con la API,
            siempre con un mensaje explicado en español.
    """
    if not cuerpo or not cuerpo.strip():
        raise ErrorGuardIA("Pegá el texto del mensaje que querés analizar.")

    if len(cuerpo) > MAX_CARACTERES:
        raise ErrorGuardIA(
            f"El mensaje es demasiado largo ({len(cuerpo):,} caracteres). "
            f"Pegá como máximo {MAX_CARACTERES:,} caracteres: alcanza con el "
            "cuerpo del correo."
        )

    mensaje_usuario = construir_mensaje_usuario(cuerpo, remitente, asunto, enlaces)

    try:
        respuesta = cliente.chat.completions.create(
            model=MODELO_TEXTO,
            temperature=TEMPERATURA,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensaje_usuario},
            ],
            # Salida dirigida: la API valida la respuesta contra el esquema
            # antes de devolverla, así que el JSON siempre llega bien formado.
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "diagnostico_phishing",
                    "strict": True,
                    "schema": ESQUEMA_DIAGNOSTICO,
                },
            },
        )
    except Exception as error:  # noqa: BLE001 - se traduce a un mensaje claro
        raise ErrorGuardIA(_traducir_error(error)) from error

    contenido = respuesta.choices[0].message.content
    if not contenido:
        raise ErrorGuardIA(
            "El modelo no devolvió una respuesta. Probá de nuevo en unos segundos."
        )

    try:
        diagnostico = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise ErrorGuardIA(
            "La respuesta del modelo no pudo interpretarse. Probá de nuevo."
        ) from error

    uso = {
        "tokens_entrada": respuesta.usage.prompt_tokens,
        "tokens_salida": respuesta.usage.completion_tokens,
        "modelo": MODELO_TEXTO,
    }
    uso["costo_usd"] = calcular_costo(uso["tokens_entrada"], uso["tokens_salida"])

    return _normalizar(diagnostico), uso


def _traducir_error(error):
    """Convierte los errores de la API en mensajes entendibles.

    La aplicación está pensada para personas sin perfil técnico: un traceback o
    un "401 Unauthorized" no le sirve a nadie. Acá se traduce cada caso
    frecuente a una explicación con la acción a seguir.

    Args:
        error: excepción original lanzada por el SDK de OpenAI.

    Returns:
        str: mensaje para mostrar en pantalla.
    """
    texto = str(error).lower()

    if "api key" in texto or "authentication" in texto or "401" in texto:
        return (
            "La clave de API no es válida o no está configurada. Revisá el valor "
            "de OPENAI_API_KEY en los secretos de la aplicación."
        )
    if "quota" in texto or "insufficient_quota" in texto or "billing" in texto:
        return (
            "La cuenta de OpenAI no tiene crédito disponible. Cargá saldo en "
            "platform.openai.com para seguir usando el análisis."
        )
    if "rate limit" in texto or "429" in texto:
        return (
            "Se hicieron demasiadas consultas seguidas. Esperá unos segundos y "
            "volvé a intentar."
        )
    if "connection" in texto or "timeout" in texto or "network" in texto:
        return (
            "No se pudo conectar con el servicio de IA. Revisá tu conexión a "
            "internet y volvé a intentar."
        )
    return f"Ocurrió un problema al analizar el mensaje: {error}"
