"""
GuardIA — Asistente anti-phishing con IA para PyMEs.
Interfaz web construida con Streamlit.

Proyecto Final · Prompt Engineering para Programadores (CoderHouse)
Autor: Agustín Idoyaga Molina — Comisión #95920

La aplicación resuelve una tarea específica: un empleado pega un correo o
mensaje que le genera dudas y recibe, en segundos, un diagnóstico estructurado
—nivel de riesgo, señales concretas, explicación en lenguaje simple y qué
hacer— generado por un modelo de IA con salida dirigida.

Este archivo contiene únicamente la interfaz. Toda la lógica (prompts, llamadas
a la API, generación de la placa) vive en el paquete `guardia/`.
"""

import html
import os
from datetime import datetime

import streamlit as st

from guardia import __version__
from guardia.analisis import (
    MODELO_TEXTO,
    PRECIO_ENTRADA_POR_MILLON,
    PRECIO_SALIDA_POR_MILLON,
    ErrorGuardIA,
    analizar_mensaje,
    crear_cliente,
)
from guardia.ejemplos import EJEMPLOS, buscar_ejemplo
from guardia.imagen import ErrorImagen, generar_placa

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
    "uso": None,           # tokens y costo de ese análisis
    "placa": None,         # placa de concientización generada (bytes PNG)
    "consultas": 0,        # cantidad de análisis en la sesión
    "costo_total": 0.0,    # costo acumulado en dólares
    "cuerpo": "",
    "remitente": "",
    "asunto": "",
    "enlaces": "",
}
for clave, valor in VALORES_INICIALES.items():
    st.session_state.setdefault(clave, valor)


def obtener_api_key():
    """Busca la clave de API en los secretos de Streamlit o en el entorno.

    En la app publicada la clave vive en los secretos de Streamlit Community
    Cloud; en desarrollo local alcanza con la variable de entorno. Nunca se
    escribe la clave en el código ni se sube al repositorio.

    Returns:
        str: la clave encontrada, o cadena vacía si no hay ninguna.
    """
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:  # noqa: BLE001 - no existe secrets.toml en local
        pass
    return os.environ.get("OPENAI_API_KEY", "")


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
    st.session_state["placa"] = None


def limpiar_formulario():
    """Deja el formulario y el resultado en blanco."""
    for clave in ("cuerpo", "remitente", "asunto", "enlaces"):
        st.session_state[clave] = ""
    st.session_state["diagnostico"] = None
    st.session_state["uso"] = None
    st.session_state["placa"] = None


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
            "Cargá `OPENAI_API_KEY` en los secretos de la app para habilitar "
            "el análisis."
        )

    st.divider()
    st.markdown("### Consumo de esta sesión")
    columna_a, columna_b = st.columns(2)
    columna_a.metric("Análisis", st.session_state["consultas"])
    columna_b.metric("Costo (US$)", f"{st.session_state['costo_total']:.4f}")
    st.caption(
        f"Modelo `{MODELO_TEXTO}` · US$ {PRECIO_ENTRADA_POR_MILLON:.2f} por millón "
        f"de tokens de entrada y US$ {PRECIO_SALIDA_POR_MILLON:.2f} de salida. "
        "El costo se calcula con los tokens reales de cada consulta."
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

    # --- Botón de acción principal (requisito de la consigna) --------------
    columna_analizar, columna_limpiar = st.columns([3, 1])
    with columna_analizar:
        analizar = st.button(
            "🔍  Analizar mensaje",
            type="primary",
            use_container_width=True,
        )
    with columna_limpiar:
        st.button("Limpiar", on_click=limpiar_formulario, use_container_width=True)

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
            st.session_state["placa"] = None
            st.session_state["consultas"] += 1
            st.session_state["costo_total"] += uso["costo_usd"]
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

        # --- Contenido adicional: placa de concientización (texto -> imagen)
        st.divider()
        st.markdown("### Convertí este caso en capacitación")
        st.caption(
            "GuardIA genera con IA una placa lista para compartir por el grupo "
            "interno de la empresa o para imprimir: así, cada intento de phishing "
            "recibido se transforma en material de concientización para todo el equipo."
        )

        if st.button("🎨  Generar placa de concientización", use_container_width=True):
            try:
                cliente = crear_cliente(obtener_api_key())
                with st.spinner("Generando la placa con IA…"):
                    placa, modelo_imagen = generar_placa(cliente, diagnostico)
                st.session_state["placa"] = placa
                st.caption(f"Ilustración generada con `{modelo_imagen}`.")
            except (ErrorGuardIA, ErrorImagen) as error:
                st.warning(str(error), icon="⚠️")

        if st.session_state["placa"]:
            st.image(st.session_state["placa"], use_container_width=True)
            st.download_button(
                "⬇️  Descargar placa (PNG)",
                data=st.session_state["placa"],
                file_name=f"guardia-placa-{datetime.now():%Y%m%d-%H%M}.png",
                mime="image/png",
                use_container_width=True,
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
                    f"{uso['tokens_entrada']} tokens de entrada + "
                    f"{uso['tokens_salida']} de salida · "
                    f"costo US$ {uso['costo_usd']:.5f}"
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
        "- **Placa de concientización** opcional, generada con IA, para compartir "
        "el caso con el resto del equipo."
    )

    st.markdown("### Cómo funciona por dentro")
    st.markdown(
        f"El texto se envía al modelo **{MODELO_TEXTO}** de OpenAI junto con un "
        "prompt que le asigna el rol de analista de ciberseguridad, le da un "
        "checklist de qué evaluar y le prohíbe inventar datos o afirmar con "
        "certeza absoluta. La respuesta se pide con **salida dirigida** "
        "(*Structured Outputs*): la API valida el resultado contra un esquema "
        "JSON antes de devolverlo, por lo que la aplicación siempre recibe la "
        "misma estructura y puede mostrarla igual en todos los casos."
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
        "- **Privacidad:** el texto se envía a la API de OpenAI para su análisis. "
        "No pegues información confidencial que no sea necesaria."
    )


# ---------------------------------------------------------------------------
# 5.3 Pestaña: acerca del proyecto
# ---------------------------------------------------------------------------
with pestana_acerca:
    st.markdown("## Acerca del proyecto")
    st.markdown(
        "**GuardIA** es el Proyecto Final del curso *Prompt Engineering para "
        "Programadores* de la Diplomatura en Inteligencia Artificial de CoderHouse."
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

    st.markdown("### Los dos modelos que integra")
    st.markdown(
        f"- **Texto → texto ({MODELO_TEXTO}):** es el núcleo. Analiza el mensaje y "
        "devuelve el diagnóstico con salida dirigida.\n"
        "- **Texto → imagen:** genera la placa de concientización a partir del "
        "resultado, para transformar cada caso real en material de capacitación."
    )

    st.markdown("### Factibilidad económica")
    st.markdown(
        f"Cada análisis consume alrededor de 1.500 tokens de entrada y 500 de "
        f"salida. Con los precios de `{MODELO_TEXTO}` "
        f"(US$ {PRECIO_ENTRADA_POR_MILLON:.2f} y US$ {PRECIO_SALIDA_POR_MILLON:.2f} "
        "por millón de tokens de entrada y salida), eso da un costo aproximado de "
        "**US$ 0,0005 por consulta**: unos **US$ 0,25 al mes** con 500 análisis. "
        "El hosting en Streamlit Community Cloud no tiene costo. La placa de "
        "concientización cuesta más por unidad, pero se genera solo cuando el "
        "usuario la pide, no en cada análisis."
    )
    st.caption(
        "La barra lateral muestra el costo real acumulado en esta sesión, "
        "calculado con los tokens efectivamente consumidos."
    )

    st.markdown("### Tecnologías")
    st.markdown(
        "Python · Streamlit · API de OpenAI (Structured Outputs) · Pillow · "
        "Streamlit Community Cloud · GitHub"
    )


# ===========================================================================
# 6. PIE DE PÁGINA
# ===========================================================================

st.markdown(
    f"""
    <div class="guardia-footer">
        <strong>GuardIA</strong> · Seguridad al alcance de cualquier PyME<br>
        Proyecto Final — Prompt Engineering para Programadores · CoderHouse ·
        Agustín Idoyaga Molina (Comisión #95920)<br>
        Análisis asistido por inteligencia artificial. Los resultados son
        orientativos: ante la duda, verificá por un canal oficial.
    </div>
    """,
    unsafe_allow_html=True,
)
