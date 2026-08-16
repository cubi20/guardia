"""
Motor de análisis de GuardIA.

Encapsula todo el contacto con la API de Gemini: creación del cliente, llamada
con salida dirigida, control de errores y medición del consumo de cada consulta.

La interfaz (app.py) no sabe nada de Gemini: solo llama a `analizar_mensaje` y
recibe un diccionario ya validado. Cambiar de proveedor implicaría reescribir
este archivo y ningún otro.
"""

import json
import time

from google import genai
from google.genai import types

from .prompts import (
    ESQUEMA_DIAGNOSTICO,
    PROMPT_SISTEMA,
    construir_mensaje_usuario,
)

# ---------------------------------------------------------------------------
# Configuración del modelo
# ---------------------------------------------------------------------------
# Se eligió la familia Flash de Gemini por dos razones: tiene un nivel gratuito
# real —suficiente para el uso previsto de la herramienta— y soporta salida
# dirigida con esquema, que es lo que hace confiable a la aplicación.
#
# La lista es un orden de preferencia: si el primer modelo no está disponible
# en la cuenta, se prueba el siguiente. Así la app no deja de funcionar cuando
# Google renombra o retira una versión.
# Se usan los alias `-latest` a propósito: Google los mantiene apuntando a la
# versión vigente de cada familia, mientras que los nombres con número de
# versión dejan de habilitarse para cuentas nuevas cuando salen los siguientes.
# El nivel gratuito da 20 consultas por día **por modelo**, así que la lista
# cumple dos funciones: cubre que un modelo deje de estar disponible y, sobre
# todo, multiplica el cupo diario. Si el primero agota su cuota, la app sigue
# funcionando con el siguiente en lugar de quedarse muda hasta el otro día.
MODELOS_TEXTO = [
    "gemini-flash-latest",       # el que se usa normalmente
    "gemini-3-flash-preview",    # alternativa de la misma familia
    "gemini-flash-lite-latest",  # más liviano y más rápido
    "gemini-3.1-flash-lite",     # último recurso del día
]

# Precios del nivel pago de la familia Flash de Gemini 3, en dólares por millón
# de tokens (agosto de 2026). En el nivel gratuito el costo es cero; estas
# constantes existen para poder mostrar cuánto costaría la herramienta si algún
# día tuviera que escalar más allá de los cupos gratuitos.
PRECIO_ENTRADA_POR_MILLON = 0.75
PRECIO_SALIDA_POR_MILLON = 3.75

# Temperatura baja: buscamos un diagnóstico estable y reproducible, no
# creatividad. El mismo correo debería recibir siempre una evaluación similar.
TEMPERATURA = 0.2

# Nivel de razonamiento previo del modelo. Se fija en bajo a propósito: medido
# sobre los correos de ejemplo, el diagnóstico es igual de bueno (mismo nivel de
# riesgo, mismas señales) pero la respuesta baja de 30-70 segundos a 4-8. Para
# alguien que duda si hacer clic, esa diferencia importa más que un matiz.
NIVEL_RAZONAMIENTO = "LOW"

# Límite defensivo de caracteres del mensaje a analizar. Evita que un pegado
# accidental de un archivo entero consuma la cuota diaria de una sola vez.
MAX_CARACTERES = 12000

# Los modelos gratuitos se saturan de a ratos y responden 503. Es un fallo
# pasajero, así que antes de darse por vencida la app reintenta con el mismo
# modelo y después pasa al siguiente de la lista.
INTENTOS_POR_MODELO = 2
ESPERA_ENTRE_INTENTOS = 2.0  # segundos


class ErrorGuardIA(Exception):
    """Error controlado y explicado en español, listo para mostrar al usuario."""


def crear_cliente(api_key):
    """Crea el cliente de Gemini.

    Args:
        api_key: clave de la API. Se toma de los secretos de Streamlit o de la
            variable de entorno GEMINI_API_KEY (ver app.py).

    Returns:
        genai.Client: cliente listo para usar.

    Raises:
        ErrorGuardIA: si no hay clave configurada.
    """
    if not api_key:
        raise ErrorGuardIA(
            "No hay una clave de API configurada. Cargá tu clave de Google AI "
            "Studio en los secretos de la aplicación (GEMINI_API_KEY) para poder "
            "analizar mensajes."
        )
    return genai.Client(api_key=api_key)


def calcular_costo(tokens_entrada, tokens_salida):
    """Calcula cuánto costaría la consulta en el nivel pago de Gemini.

    En el nivel gratuito el costo real es cero. Este cálculo se muestra en la
    aplicación como referencia de escalabilidad: responde a la pregunta "¿y si
    esto lo usaran mil personas?".

    Args:
        tokens_entrada: tokens del prompt enviado.
        tokens_salida: tokens generados por el modelo.

    Returns:
        float: costo equivalente de la consulta en dólares.
    """
    return (
        tokens_entrada * PRECIO_ENTRADA_POR_MILLON
        + tokens_salida * PRECIO_SALIDA_POR_MILLON
    ) / 1_000_000


def _normalizar(diagnostico):
    """Ajusta valores fuera de rango y mantiene la coherencia del resultado.

    La salida dirigida garantiza la estructura del JSON, pero no que el puntaje
    esté dentro de 0-100. Esta función es la última línea de defensa antes de
    mostrar el resultado en pantalla.

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

    Es la función principal del proyecto: toma el texto que pegó el usuario, lo
    envía al modelo junto con el prompt especializado y devuelve un diccionario
    con la misma forma siempre, gracias a la salida dirigida.

    Args:
        cliente: instancia creada con `crear_cliente`.
        cuerpo: texto del mensaje a analizar.
        remitente: remitente del mensaje (opcional).
        asunto: asunto del mensaje (opcional).
        enlaces: enlaces incluidos en el mensaje (opcional).

    Returns:
        tuple[dict, dict]: (diagnóstico, uso) donde `uso` trae los tokens
        consumidos y el costo equivalente de la consulta.

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

    configuracion = types.GenerateContentConfig(
        system_instruction=PROMPT_SISTEMA,
        temperature=TEMPERATURA,
        # Salida dirigida: la API valida la respuesta contra el esquema antes
        # de devolverla, así que el JSON siempre llega con la forma esperada.
        response_mime_type="application/json",
        response_schema=ESQUEMA_DIAGNOSTICO,
        thinking_config=types.ThinkingConfig(thinking_level=NIVEL_RAZONAMIENTO),
    )

    respuesta, modelo_usado, ultimo_error = None, None, None
    for modelo in MODELOS_TEXTO:
        for intento in range(INTENTOS_POR_MODELO):
            try:
                respuesta = cliente.models.generate_content(
                    model=modelo,
                    contents=mensaje_usuario,
                    config=configuracion,
                )
                modelo_usado = modelo
                break
            except Exception as error:  # noqa: BLE001 - se decide según el tipo
                ultimo_error = error
                # Problemas de clave, permisos o cuota son comunes a todos los
                # modelos: reintentar no aporta nada y solo demora la respuesta.
                if not _es_recuperable(error):
                    raise ErrorGuardIA(_traducir_error(error)) from error
                # Sobrecarga pasajera: esperamos un momento y reintentamos con
                # el mismo modelo. Si en cambio se agotó su cuota diaria o el
                # modelo ya no existe, reintentar es inútil: se pasa al siguiente.
                if _es_sobrecarga(error) and intento + 1 < INTENTOS_POR_MODELO:
                    time.sleep(ESPERA_ENTRE_INTENTOS)
                    continue
                break  # probamos el siguiente modelo de la lista
        if respuesta is not None:
            break

    if respuesta is None:
        raise ErrorGuardIA(_traducir_error(ultimo_error))

    contenido = respuesta.text
    if not contenido:
        raise ErrorGuardIA(
            "El modelo no devolvió una respuesta. Puede haber filtrado el "
            "contenido del mensaje. Probá de nuevo o con otro texto."
        )

    try:
        diagnostico = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise ErrorGuardIA(
            "La respuesta del modelo no pudo interpretarse. Probá de nuevo."
        ) from error

    uso = _medir_uso(respuesta, modelo_usado)
    return _normalizar(diagnostico), uso


def _medir_uso(respuesta, modelo):
    """Extrae los tokens consumidos y calcula el costo equivalente.

    Args:
        respuesta: objeto devuelto por `generate_content`.
        modelo: nombre del modelo que respondió.

    Returns:
        dict: tokens de entrada y salida, modelo y costo equivalente.
    """
    metadatos = getattr(respuesta, "usage_metadata", None)
    entrada = getattr(metadatos, "prompt_token_count", 0) or 0
    salida = getattr(metadatos, "candidates_token_count", 0) or 0
    # Los modelos de razonamiento cuentan aparte los tokens de "pensamiento":
    # se suman a la salida porque en el nivel pago se facturan como tal.
    salida += getattr(metadatos, "thoughts_token_count", 0) or 0

    return {
        "tokens_entrada": entrada,
        "tokens_salida": salida,
        "modelo": modelo,
        "costo_usd": calcular_costo(entrada, salida),
    }


def _es_sobrecarga(error):
    """Indica si el modelo está momentáneamente saturado.

    Args:
        error: excepción lanzada por el SDK.

    Returns:
        bool: True si vale la pena reintentar la misma llamada.
    """
    texto = str(error).lower()
    return "503" in texto or "unavailable" in texto or "overloaded" in texto


def _es_modelo_no_disponible(error):
    """Indica si el error significa que ese modelo puntual no existe.

    Args:
        error: excepción lanzada por el SDK.

    Returns:
        bool: True si conviene probar con el siguiente modelo de la lista.
    """
    texto = str(error).lower()
    return "not_found" in texto or "404" in texto or "is not found" in texto


def _es_cuota_agotada(error):
    """Indica si el modelo agotó su cuota gratuita del día.

    Args:
        error: excepción lanzada por el SDK.

    Returns:
        bool: True si conviene pasar a otro modelo, que tiene su propio cupo.
    """
    texto = str(error).lower()
    return "resource_exhausted" in texto or "429" in texto or "quota" in texto


def _es_recuperable(error):
    """Indica si tiene sentido seguir intentando con otro modelo u otra vuelta.

    Args:
        error: excepción lanzada por el SDK.

    Returns:
        bool: False para los errores que se van a repetir igual con cualquier
        modelo (clave inválida, sin permisos): esos se informan de inmediato.
    """
    return (
        _es_modelo_no_disponible(error)
        or _es_sobrecarga(error)
        or _es_cuota_agotada(error)
    )


def _traducir_error(error):
    """Convierte los errores de la API en mensajes entendibles.

    La aplicación está pensada para personas sin perfil técnico: un traceback o
    un "429 RESOURCE_EXHAUSTED" no le sirve a nadie. Acá se traduce cada caso
    frecuente a una explicación con la acción a seguir.

    Args:
        error: excepción original lanzada por el SDK.

    Returns:
        str: mensaje para mostrar en pantalla.
    """
    texto = str(error).lower()

    if "api key" in texto or "api_key" in texto or "unauthenticated" in texto or "401" in texto:
        return (
            "La clave de API no es válida o no está configurada. Revisá el valor "
            "de GEMINI_API_KEY en los secretos de la aplicación."
        )
    if "permission" in texto or "403" in texto:
        return (
            "La clave no tiene permiso para usar este modelo. Generá una nueva "
            "clave en Google AI Studio y volvé a cargarla."
        )
    if "not_found" in texto or "404" in texto:
        return (
            "Ninguno de los modelos configurados está disponible para esta clave "
            f"({', '.join(MODELOS_TEXTO)}). Google retira los modelos viejos para "
            "las cuentas nuevas: revisá la lista MODELOS_TEXTO en analisis.py."
        )
    if "resource_exhausted" in texto or "quota" in texto or "429" in texto:
        return (
            "Se agotó el cupo gratuito de hoy en todos los modelos disponibles "
            f"({len(MODELOS_TEXTO)} modelos × 20 consultas por día). El cupo se "
            "renueva a la medianoche del Pacífico, cerca de las 4 de la mañana "
            "en Argentina."
        )
    if "503" in texto or "unavailable" in texto or "overloaded" in texto:
        return (
            "El servicio de IA está con mucha demanda en este momento. Esperá "
            "unos segundos y volvé a intentar: suele resolverse solo."
        )
    if "connection" in texto or "timeout" in texto or "network" in texto:
        return (
            "No se pudo conectar con el servicio de IA. Revisá tu conexión a "
            "internet y volvé a intentar."
        )
    if "safety" in texto or "blocked" in texto:
        return (
            "El servicio bloqueó el contenido del mensaje. Probá pegando solo el "
            "cuerpo del correo, sin datos personales."
        )
    return f"Ocurrió un problema al analizar el mensaje: {error}"
