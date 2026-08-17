"""
GuardIA — Asistente anti-phishing con IA para PyMEs.
Interfaz web construida con Streamlit.

Proyecto Final · Inteligencia artificial: Generación de Prompts (CoderHouse)
Autor: Agustín Idoyaga Molina — Comisión #95920

La aplicación resuelve una tarea específica: un empleado pega un correo o
mensaje que le genera dudas y recibe, en segundos, un diagnóstico estructurado
—nivel de riesgo, señales concretas, explicación en lenguaje simple y qué
hacer— generado por un modelo de IA con salida dirigida.

Este archivo contiene únicamente la interfaz. Toda la lógica (prompts, llamadas
a la API) vive en el paquete `guardia/`.
"""

import html
import os
from datetime import datetime

import streamlit as st

from guardia import __version__
from guardia.analisis import (
    MODELOS_TEXTO,
    PRECIO_ENTRADA_POR_MILLON,
    PRECIO_SALIDA_POR_MILLON,
    ErrorGuardIA,
    analizar_mensaje,
    crear_cliente,
)
from guardia.ejemplos import EJEMPLOS, buscar_ejemplo

# Modelo que se usa normalmente; si no estuviera disponible, `analizar_mensaje`
# prueba los siguientes de la lista y el resultado informa cuál respondió.
MODELO_TEXTO = MODELOS_TEXTO[0]

# ===========================================================================
# 1. CONFIGURACIÓN GENERAL Y ESTILOS
# ===========================================================================

st.set_page_config(
    page_title="GuardIA · Asistente anti-phishing",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Paleta de la marca: azul profundo (confianza, seguridad) + verde azulado
# (acción). Se define una sola vez acá y se reutiliza en toda la interfaz.
ESTILOS = """
<style>
    :root {
        --azul: #0B2E4F;
        --verde: #1F7A8C;
        --claro: #F4F7F9;
        --texto: #26323E;
    }

    /* --- Encabezado de la aplicación --- */
    .guardia-header {
        background: linear-gradient(120deg, #0B2E4F 0%, #1F7A8C 100%);
        border-radius: 14px;
        padding: 30px 34px;
        margin-bottom: 22px;
        color: #FFFFFF;
    }
    .guardia-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
    }
    .guardia-header h1 span { color: #8FD3E0; }
    .guardia-header p {
        margin: 6px 0 0 0;
        font-size: 1.05rem;
        color: #D8E7EE;
    }

    /* --- Tarjeta de resultado --- */
    .tarjeta {
        background: var(--claro);
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 5px solid var(--verde);
        margin-bottom: 14px;
    }
    .tarjeta h4 { margin: 0 0 8px 0; color: var(--azul); font-size: 1rem; }
    .tarjeta p  { margin: 0; color: var(--texto); line-height: 1.55; }

    /* --- Etiqueta de nivel de riesgo --- */
    .etiqueta-riesgo {
        display: inline-block;
        padding: 8px 20px;
        border-radius: 30px;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.5px;
    }

    /* --- Barra de puntaje --- */
    .barra-fondo {
        background: #DFE6EC;
        border-radius: 8px;
        height: 14px;
        width: 100%;
        margin-top: 10px;
        overflow: hidden;
    }
    .barra-relleno { height: 14px; border-radius: 8px; }

    /* --- Señales detectadas --- */
    .senal {
        border: 1px solid #E1E8ED;
        border-left: 4px solid var(--verde);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        background: #FFFFFF;
    }
    .senal strong { color: var(--azul); }
    .senal small  { color: #667A8A; }
    .senal p { margin: 4px 0 0 0; color: var(--texto); font-size: 0.93rem; }

    /* --- Pie de página --- */
    .guardia-footer {
        margin-top: 44px;
        padding-top: 18px;
        border-top: 1px solid #DFE6EC;
        color: #6B7C8C;
        font-size: 0.85rem;
        text-align: center;
        line-height: 1.6;
    }
</style>
"""
st.markdown(ESTILOS, unsafe_allow_html=True)

# Colores de cada nivel de riesgo, compartidos por la etiqueta y la barra.
COLORES_RIESGO = {
    "alto": "#C0392B",
    "medio": "#D68910",
    "bajo": "#1E8449",
    "indeterminado": "#5A6876",
}


# ===========================================================================
# 2. ESTADO DE LA SESIÓN
# ===========================================================================
# Streamlit vuelve a ejecutar el script entero con cada interacción, así que
# todo lo que tiene que sobrevivir a un clic se guarda en st.session_state.

VALORES_INICIALES = {
    "diagnostico": None,   # último análisis realizado
    "uso": None,           # tokens consumidos por ese análisis
    "consultas": 0,        # cantidad de análisis en la sesión
    "tokens_total": 0,     # tokens acumulados en la sesión
    "costo_total": 0.0,    # costo equivalente en el nivel pago
    "cuerpo": "",
    "remitente": "",
    "asunto": "",
    "enlaces": "",
}
for clave, valor in VALORES_INICIALES.items():
    st.session_state.setdefault(clave, valor)


# Nota sobre el símbolo del dólar: Streamlit interpreta $...$ como LaTeX, así que
# en cualquier texto con dos o más "US$" hay que escribirlo escapado (US\$) o el
# símbolo desaparece y el texto del medio se renderiza como una fórmula.


def formato_numero(valor, decimales=0):
    """Formatea un número al estilo local: punto para miles, coma para decimales.

    Python formatea al estilo inglés (1,309.5) y la app está escrita en español,
    donde se escribe 1.309,5. Se formatea primero al estilo inglés y después se
    intercambian los separadores.

    Args:
        valor: número a formatear.
        decimales: cantidad de decimales a mostrar.

    Returns:
        str: el número listo para mostrar en pantalla.
    """
    return f"{valor:,.{decimales}f}".translate(str.maketrans({",": ".", ".": ","}))


def obtener_api_key():
    """Busca la clave de API en los secretos de Streamlit o en el entorno.

    En la app publicada la clave vive en los secretos de Streamlit Community
    Cloud; en desarrollo local alcanza con el archivo .streamlit/secrets.toml o
    la variable de entorno. Nunca se escribe la clave en el código ni se sube al
    repositorio.

    Returns:
        str: la clave encontrada, o cadena vacía si no hay ninguna.
    """
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:  # noqa: BLE001 - no existe secrets.toml en local
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def cargar_ejemplo():
    """Vuelca el ejemplo elegido en los campos del formulario."""
    ejemplo = buscar_ejemplo(st.session_state.get("selector_ejemplo", ""))
    if not ejemplo:
        return
    st.session_state["cuerpo"] = ejemplo["cuerpo"]
    st.session_state["remitente"] = ejemplo["remitente"]
    st.session_state["asunto"] = ejemplo["asunto"]
    st.session_state["enlaces"] = ejemplo["enlaces"]
    st.session_state["diagnostico"] = None


def limpiar_formulario():
    """Deja el formulario y el resultado en blanco."""
    for clave in ("cuerpo", "remitente", "asunto", "enlaces"):
        st.session_state[clave] = ""
    st.session_state["diagnostico"] = None
    st.session_state["uso"] = None


# ===========================================================================
# 3. ENCABEZADO Y DESCRIPCIÓN
# ===========================================================================

st.markdown(
    """
    <div class="guardia-header">
        <h1>Guard<span>IA</span></h1>
        <p>Asistente anti-phishing con inteligencia artificial, para empresas
        que no tienen un equipo de seguridad informática.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "**¿Recibiste un correo o mensaje y no sabés si es confiable?** "
    "Pegalo acá abajo y GuardIA lo analiza en segundos: te dice qué tan riesgoso "
    "es, qué señales concretas encontró, te lo explica en palabras simples y te "
    "indica qué hacer. No necesitás saber nada de seguridad informática."
)

# ===========================================================================
# 4. BARRA LATERAL: estado, consumo y ayuda rápida
# ===========================================================================

with st.sidebar:
    st.markdown("### 🛡️ GuardIA")
    st.caption(f"Versión {__version__} · Proyecto Final CoderHouse")

    api_key = obtener_api_key()
    if api_key:
        st.success("Servicio de IA conectado", icon="✅")
    else:
        st.error("Falta configurar la clave de API", icon="⚠️")
        st.caption(
            "Cargá `GEMINI_API_KEY` en los secretos de la app para habilitar "
            "el análisis."
        )

    st.divider()
    st.markdown("### Consumo de esta sesión")
    columna_a, columna_b = st.columns(2)
    columna_a.metric("Análisis", st.session_state["consultas"])
    columna_b.metric("Costo", "US$ 0")  # nivel gratuito: siempre cero
    st.caption(
        f"Modelo `{MODELO_TEXTO}`, nivel gratuito: las consultas no tienen costo. "
        f"Los {formato_numero(st.session_state['tokens_total'])} tokens usados en "
        f"esta sesión equivaldrían a US\\$ "
        f"{formato_numero(st.session_state['costo_total'], 4)} en el nivel pago, "
        "que es la referencia para estimar cuánto costaría escalar la herramienta."
    )

    st.divider()
    st.markdown("### Antes de pegar un mensaje")
    st.markdown(
        "- No incluyas datos personales que no hagan falta para el análisis.\n"
        "- GuardIA es un **asistente**, no un veredicto final.\n"
        "- Ante la duda, verificá siempre por un canal oficial."
    )

# ===========================================================================
# 5. PESTAÑAS PRINCIPALES
# ===========================================================================

pestana_analizar, pestana_como, pestana_acerca = st.tabs(
    ["🔍 Analizar mensaje", "❓ Cómo funciona", "📄 Acerca del proyecto"]
)


# ---------------------------------------------------------------------------
# 5.1 Pestaña: analizar un mensaje
# ---------------------------------------------------------------------------
with pestana_analizar:
    st.markdown("#### Pegá el mensaje sospechoso")

    st.selectbox(
        "¿No tenés uno a mano? Probá con un ejemplo",
        options=[""] + [ejemplo["nombre"] for ejemplo in EJEMPLOS],
        format_func=lambda x: "Elegí un ejemplo…" if x == "" else x,
        key="selector_ejemplo",
        on_change=cargar_ejemplo,
        help="Los ejemplos son ficticios e incluyen casos de fraude y también "
        "correos legítimos, para ver cómo responde la herramienta en ambos casos.",
    )

    # Los campos y el botón van dentro de un formulario a propósito. Fuera de él,
    # Streamlit no toma el texto del área hasta que pierde el foco: el primer clic
    # en "Analizar" solo confirmaba el texto y había que apretar dos veces. Dentro
    # del formulario, el envío confirma todos los campos y dispara el análisis en
    # una sola acción, que es lo que espera cualquier persona que lo usa.
    with st.form("formulario_analisis", border=False):
        st.text_area(
            "Cuerpo del mensaje *",
            key="cuerpo",
            height=220,
            placeholder="Pegá acá el texto completo del correo o del mensaje…",
        )

        with st.expander("Agregar remitente, asunto y enlaces (recomendado)"):
            st.caption(
                "Cuantos más datos aportes, más precisa es la evaluación: buena parte "
                "de las señales de phishing están en el remitente y en los enlaces."
            )
            st.text_input(
                "Remitente",
                key="remitente",
                placeholder="Nombre <direccion@dominio.com> o número de teléfono",
            )
            st.text_input("Asunto", key="asunto", placeholder="Asunto del correo")
            st.text_area(
                "Enlaces incluidos",
                key="enlaces",
                height=80,
                placeholder="Pegá acá las URLs del mensaje, una por línea",
            )

        # --- Botón de acción principal (requisito de la consigna) ----------
        columna_analizar, columna_limpiar = st.columns([3, 1])
        with columna_analizar:
            analizar = st.form_submit_button(
                "🔍  Analizar mensaje",
                type="primary",
                use_container_width=True,
            )
        with columna_limpiar:
            st.form_submit_button(
                "Limpiar", on_click=limpiar_formulario, use_container_width=True
            )

    # --- Ejecución del análisis -------------------------------------------
    if analizar:
        try:
            cliente = crear_cliente(obtener_api_key())
            with st.spinner("Analizando el mensaje con IA…"):
                diagnostico, uso = analizar_mensaje(
                    cliente,
                    st.session_state["cuerpo"],
                    st.session_state["remitente"],
                    st.session_state["asunto"],
                    st.session_state["enlaces"],
                )
            st.session_state["diagnostico"] = diagnostico
            st.session_state["uso"] = uso
            st.session_state["consultas"] += 1
            st.session_state["tokens_total"] += (
                uso["tokens_entrada"] + uso["tokens_salida"]
            )
            st.session_state["costo_total"] += uso["costo_usd"]
            # La barra lateral se dibuja antes que esta parte del script, así que
            # sin este rerun el contador de consumo quedaría una consulta atrasado.
            st.rerun()
        except ErrorGuardIA as error:
            st.error(str(error), icon="⚠️")

    # --- Resultado ---------------------------------------------------------
    diagnostico = st.session_state["diagnostico"]
    if diagnostico:
        st.divider()
        st.markdown("### Resultado del análisis")

        nivel = diagnostico["nivel_riesgo"]
        puntaje = diagnostico["puntaje"]
        color = COLORES_RIESGO.get(nivel, COLORES_RIESGO["indeterminado"])

        columna_etiqueta, columna_tipo = st.columns([1, 2])
        with columna_etiqueta:
            st.markdown(
                f'<span class="etiqueta-riesgo" style="background:{color}">'
                f"RIESGO {html.escape(nivel.upper())}</span>",
                unsafe_allow_html=True,
            )
        with columna_tipo:
            st.markdown(
                f"**Tipo de engaño detectado:** "
                f"{html.escape(diagnostico.get('tipo_de_engano', '—'))}"
            )

        st.markdown(
            f"<div class='barra-fondo'><div class='barra-relleno' "
            f"style='width:{puntaje}%;background:{color}'></div></div>"
            f"<small style='color:#667A8A'>Puntaje de riesgo: "
            f"<strong>{puntaje}/100</strong></small>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Qué significa")
        st.markdown(
            f"<div class='tarjeta'><p>"
            f"{html.escape(diagnostico['explicacion'])}</p></div>",
            unsafe_allow_html=True,
        )

        senales = diagnostico.get("senales", [])
        st.markdown(f"#### Señales detectadas ({len(senales)})")
        if senales:
            for senal in senales:
                st.markdown(
                    "<div class='senal'>"
                    f"<strong>{html.escape(senal.get('titulo', ''))}</strong> "
                    f"<small>· gravedad {html.escape(senal.get('gravedad', '—'))}</small>"
                    f"<p>{html.escape(senal.get('detalle', ''))}</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(
                "No se detectaron señales relevantes. Recordá que la ausencia de "
                "señales no garantiza que el mensaje sea legítimo.",
                icon="ℹ️",
            )

        st.markdown("#### Qué hacer ahora")
        st.markdown(
            f"<div class='tarjeta' style='border-left-color:{color}'>"
            f"<h4>Recomendación</h4><p>"
            f"{html.escape(diagnostico['recomendacion'])}</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='tarjeta'><h4>Cómo verificarlo</h4><p>"
            f"{html.escape(diagnostico['verificacion_sugerida'])}</p></div>",
            unsafe_allow_html=True,
        )

        # --- Informe descargable y detalle de consumo -------------------------
        st.divider()
        informe = [
            "INFORME DE ANÁLISIS - GuardIA",
            f"Fecha: {datetime.now():%d/%m/%Y %H:%M}",
            "",
            f"Nivel de riesgo: {nivel.upper()} ({puntaje}/100)",
            f"Tipo de engaño: {diagnostico.get('tipo_de_engano', '—')}",
            "",
            "Explicación:",
            diagnostico["explicacion"],
            "",
            "Señales detectadas:",
        ]
        informe += [
            f"  - [{s.get('gravedad', '—')}] {s.get('titulo', '')}: {s.get('detalle', '')}"
            for s in senales
        ] or ["  - Ninguna."]
        informe += [
            "",
            f"Recomendación: {diagnostico['recomendacion']}",
            f"Verificación sugerida: {diagnostico['verificacion_sugerida']}",
            "",
            "GuardIA es un asistente de apoyo. No reemplaza la verificación por",
            "un canal oficial ni las defensas técnicas de la organización.",
        ]

        columna_informe, columna_consumo = st.columns([1, 1])
        with columna_informe:
            st.download_button(
                "⬇️  Descargar informe (TXT)",
                data="\n".join(informe),
                file_name=f"guardia-informe-{datetime.now():%Y%m%d-%H%M}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with columna_consumo:
            uso = st.session_state["uso"]
            if uso:
                st.caption(
                    f"Consulta procesada con `{uso['modelo']}` · "
                    f"{formato_numero(uso['tokens_entrada'])} tokens de entrada + "
                    f"{formato_numero(uso['tokens_salida'])} de salida · "
                    f"costo US\\$ 0 (nivel gratuito; equivaldría a "
                    f"US\\$ {formato_numero(uso['costo_usd'], 5)} en el nivel pago)"
                )


# ---------------------------------------------------------------------------
# 5.2 Pestaña: cómo funciona (requisito de la consigna)
# ---------------------------------------------------------------------------
with pestana_como:
    st.markdown("## Cómo funciona GuardIA")
    st.markdown(
        "GuardIA es un asistente que analiza correos y mensajes sospechosos con "
        "inteligencia artificial y devuelve un diagnóstico entendible para "
        "cualquier persona, sin conocimientos técnicos."
    )

    st.markdown("### En tres pasos")
    paso_uno, paso_dos, paso_tres = st.columns(3)
    paso_uno.markdown(
        "**1. Pegás el mensaje**\n\nCopiás el correo o mensaje que te genera dudas. "
        "Si podés, agregá también el remitente y los enlaces."
    )
    paso_dos.markdown(
        "**2. La IA lo analiza**\n\nRevisa el dominio del remitente, la urgencia, "
        "qué te piden, los enlaces y la redacción."
    )
    paso_tres.markdown(
        "**3. Recibís el veredicto**\n\nNivel de riesgo, señales concretas, "
        "explicación simple y una acción para hacer ahora."
    )

    st.markdown("### Cómo hacer una buena consulta")
    st.markdown(
        "- **Pegá el mensaje completo**, no un resumen: las señales suelen estar "
        "en los detalles (una palabra de urgencia, una letra cambiada en el dominio).\n"
        "- **Sumá el remitente y los enlaces.** Muchos fraudes se detectan justamente "
        "ahí y no en el cuerpo del texto.\n"
        "- **Sacá los datos personales que no hagan falta** (números de documento, "
        "de cuenta o de tarjeta) antes de pegar el mensaje.\n"
        "- **Un mensaje por consulta.** Si tenés varios correos para revisar, "
        "analizalos de a uno."
    )

    st.markdown("### Qué vas a recibir")
    st.markdown(
        "- **Nivel de riesgo y puntaje** (bajo, medio o alto, de 0 a 100).\n"
        "- **Tipo de engaño detectado**, por ejemplo *suplantación de banco* o "
        "*cambio de CBU*.\n"
        "- **Señales concretas**, cada una con su gravedad y con la parte del "
        "mensaje que la dispara.\n"
        "- **Explicación en lenguaje simple**, sin jerga técnica.\n"
        "- **Recomendación y verificación sugerida**: qué hacer ahora y cómo "
        "confirmarlo por un canal oficial.\n"
        "- **Un informe descargable** en texto, para archivar el caso o "
        "reenviarlo a quien corresponda."
    )

    st.markdown("### Cómo funciona por dentro")
    st.markdown(
        f"El texto se envía al modelo **{MODELO_TEXTO}** de Google junto con un "
        "prompt que le asigna el rol de analista de ciberseguridad, le da un "
        "checklist de qué evaluar y le prohíbe inventar datos o afirmar con "
        "certeza absoluta. La respuesta se pide con **salida dirigida** "
        "(*structured output*): se envía un esquema junto con la consulta y la "
        "API garantiza que el resultado lo cumpla, por lo que la aplicación "
        "siempre recibe la misma estructura y puede mostrarla igual en todos "
        "los casos."
    )
    st.code(
        """{
  "nivel_riesgo": "bajo | medio | alto | indeterminado",
  "puntaje": 0-100,
  "tipo_de_engano": "técnica detectada",
  "senales": [{"titulo": "...", "detalle": "...", "gravedad": "baja|media|alta"}],
  "explicacion": "en lenguaje simple, no técnico",
  "recomendacion": "qué hacer ahora",
  "verificacion_sugerida": "cómo confirmarlo por un canal oficial"
}""",
        language="json",
    )

    st.markdown("### Límites que conviene tener presentes")
    st.warning(
        "**GuardIA es un asistente, no un veredicto final.** El modelo puede "
        "equivocarse: puede marcar como sospechoso un correo legítimo, o dejar "
        "pasar uno malicioso. Ante cualquier duda, verificá por un canal oficial "
        "que ya conozcas, nunca por los datos de contacto que aparecen en el "
        "mensaje.",
        icon="⚠️",
    )
    st.markdown(
        "- **Analiza texto, no archivos.** No abre adjuntos ni sigue enlaces: "
        "evalúa lo que ve escrito.\n"
        "- **No reemplaza** al antivirus, a los filtros de correo ni al segundo "
        "factor de autenticación (MFA). Los complementa en el punto donde esas "
        "defensas no llegan: la decisión de la persona.\n"
        "- **El phishing evoluciona.** El prompt y los ejemplos se actualizan para "
        "no perder efectividad.\n"
        "- **El nivel gratuito tiene cupo diario.** Son 20 consultas por día por "
        "modelo; la app usa varios en cascada, así que el cupo real es mayor. Si "
        "se agota, se renueva a la madrugada.\n"
        "- **Privacidad:** el texto se envía a la API de Google Gemini para su "
        "análisis. No pegues información confidencial que no sea necesaria."
    )


# ---------------------------------------------------------------------------
# 5.3 Pestaña: acerca del proyecto
# ---------------------------------------------------------------------------
with pestana_acerca:
    st.markdown("## Acerca del proyecto")
    st.markdown(
        "**GuardIA** es el Proyecto Final del curso *Inteligencia artificial: Generación de Prompts* "
        "de la Diplomatura en Inteligencia Artificial de CoderHouse."
    )
    st.markdown(
        "- **Estudiante:** Agustín Idoyaga Molina\n"
        "- **Comisión:** #95920\n"
        f"- **Versión de la aplicación:** {__version__}"
    )

    st.markdown("### La problemática")
    st.markdown(
        "El phishing es una de las principales puertas de entrada a los ataques "
        "informáticos, y las PyMEs son el eslabón más vulnerable: rara vez tienen "
        "un equipo de seguridad, un plan de capacitación o presupuesto para "
        "herramientas comerciales. Según el *Verizon Data Breach Investigations "
        "Report* 2025, alrededor del 60% de las brechas involucran el factor "
        "humano y el 88% de las brechas en pequeñas y medianas empresas incluyen "
        "ransomware, que en muchos casos empieza con un simple correo."
    )
    st.markdown(
        "La paradoja es que la IA generativa volvió el phishing mucho más "
        "convincente: los mensajes fraudulentos ya no se detectan por su mala "
        "redacción. Si la IA hizo más difícil el problema, tiene sentido usar esa "
        "misma tecnología para resolverlo."
    )

    st.markdown("### Cómo se integra la IA")
    st.markdown(
        f"El núcleo de la aplicación es el modelo **{MODELO_TEXTO}**, de la "
        "familia Flash de Google. Analiza el mensaje y devuelve el diagnóstico "
        "con **salida dirigida**: junto con la consulta se envía el esquema de "
        "la respuesta, y la API garantiza que el resultado lo cumpla. Eso es lo "
        "que convierte una respuesta de chat en una funcionalidad confiable."
    )

    st.markdown("### Factibilidad económica")
    st.markdown(
        "**El costo de operación es cero.** El nivel gratuito de la API de "
        "Gemini cubre el uso previsto de la herramienta —20 consultas por día "
        "por modelo, y la app usa varios en cascada— y el hosting en Streamlit "
        "Community Cloud tampoco tiene costo. No hace falta tarjeta de crédito "
        "para poner la aplicación en producción."
    )
    st.markdown(
        f"Como referencia de escalabilidad: medido sobre los correos de ejemplo, "
        f"cada análisis consume unos 1.250 tokens. En el nivel pago "
        f"(US\\$ {formato_numero(PRECIO_ENTRADA_POR_MILLON, 2)} y "
        f"US\\$ {formato_numero(PRECIO_SALIDA_POR_MILLON, 2)} por millón de tokens de entrada y "
        "salida) eso serían unos **US\\$ 0,0022 por consulta**, poco más de "
        "**US\\$ 1 al mes** con 500 análisis. Incluso pagando, el costo es "
        "marginal frente al de un solo incidente de seguridad."
    )
    st.caption(
        "La barra lateral muestra los tokens realmente consumidos en esta "
        "sesión y su costo equivalente."
    )

    st.markdown("### Trabajo futuro")
    st.markdown(
        "La próxima función prevista es la **placa de concientización**: una "
        "pieza visual generada con un modelo texto → imagen a partir del "
        "diagnóstico, para que el responsable de la PyME pueda compartirla por "
        "el grupo interno y convertir cada intento de phishing recibido en "
        "material de capacitación para todo el equipo. Quedó fuera de esta "
        "versión porque la generación de imágenes no está disponible en los "
        "niveles gratuitos, y mantener la herramienta sin costo es parte de su "
        "propuesta de valor para una PyME."
    )

    st.markdown("### Tecnologías")
    st.markdown(
        "Python · Streamlit · API de Google Gemini (salida dirigida con "
        "esquema) · Streamlit Community Cloud · GitHub"
    )


# ===========================================================================
# 6. PIE DE PÁGINA
# ===========================================================================

st.markdown(
    f"""
    <div class="guardia-footer">
        <strong>GuardIA</strong> · Seguridad al alcance de cualquier PyME<br>
        Proyecto Final — Inteligencia artificial: Generación de Prompts · CoderHouse ·
        Agustín Idoyaga Molina (Comisión #95920)<br>
        Análisis asistido por inteligencia artificial. Los resultados son
        orientativos: ante la duda, verificá por un canal oficial.
    </div>
    """,
    unsafe_allow_html=True,
)
