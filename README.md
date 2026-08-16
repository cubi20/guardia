# 🛡️ GuardIA — Asistente anti-phishing con IA para PyMEs

> Proyecto Final · **Prompt Engineering para Programadores** — Diplomatura en Inteligencia Artificial, CoderHouse
> Estudiante: **Agustín Idoyaga Molina** · Comisión **#95920**

GuardIA es una aplicación web donde cualquier empleado pega un correo o mensaje
sospechoso y, en segundos, recibe un diagnóstico claro: **qué tan riesgoso es,
qué señales concretas se detectaron, una explicación en lenguaje simple y qué
hacer al respecto**.

🔗 **App en línea:** _(completar con el enlace de Streamlit Community Cloud)_
📦 **Código fuente:** https://github.com/cubi20/guardia

---

## El problema

El phishing es una de las principales puertas de entrada a los ataques
informáticos, y las PyMEs son el eslabón más vulnerable: rara vez tienen equipo
de seguridad, plan de capacitación o presupuesto para herramientas comerciales.
Según el *Verizon Data Breach Investigations Report* 2025, alrededor del **60%**
de las brechas involucran el factor humano y el **88%** de las brechas en
pequeñas y medianas empresas incluyen ransomware, que muchas veces empieza con
un simple correo.

La paradoja: la IA generativa volvió el phishing mucho más convincente, porque
los mensajes fraudulentos ya no se detectan por su mala redacción. Si la IA hizo
más difícil el problema, tiene sentido usar esa misma tecnología para resolverlo.

## La solución

| | |
|---|---|
| **1. Pegás el mensaje** | El correo o mensaje que genera dudas, con remitente y enlaces si los hay. |
| **2. La IA lo analiza** | Revisa dominio del remitente, urgencia, qué se pide, enlaces y redacción. |
| **3. Recibís el veredicto** | Nivel de riesgo, señales concretas, explicación simple y qué hacer ahora. |

## Cómo se integra la IA

El texto se envía a **`gemini-2.5-flash`** junto con un prompt que le asigna el
rol de analista de ciberseguridad, le da un checklist de qué evaluar y le
prohíbe inventar datos o afirmar con certeza absoluta.

### Salida dirigida

En lugar de pedirle al modelo "respondeme en JSON" y confiar en que obedezca, se
envía un **esquema de respuesta** junto con la consulta
(`response_schema` + `response_mime_type="application/json"`) y la API garantiza
que el resultado lo cumpla. Así la interfaz siempre recibe la misma estructura y
puede dibujarla igual en todos los casos, sin parsear texto libre.

```json
{
  "tipo_de_engano": "técnica detectada",
  "senales": [{"titulo": "...", "detalle": "...", "gravedad": "baja|media|alta"}],
  "puntaje": 0-100,
  "nivel_riesgo": "bajo | medio | alto | indeterminado",
  "explicacion": "en lenguaje simple, no técnico",
  "recomendacion": "qué hacer ahora",
  "verificacion_sugerida": "cómo confirmarlo por un canal oficial"
}
```

El orden de los campos no es casual: `propertyOrdering` hace que el modelo
primero detecte las señales, después puntúe y recién al final redacte la
explicación, de modo que el texto se apoye en lo que ya identificó.

## Estructura del proyecto

```
GuardIA/
├── app.py                      Interfaz web (Streamlit): header, formulario,
│                               resultado, "cómo funciona" y footer.
├── guardia/
│   ├── __init__.py
│   ├── prompts.py              Prompt principal y esquema de la salida dirigida.
│   ├── analisis.py             Cliente de Gemini, análisis y medición del consumo.
│   └── ejemplos.py             Mensajes de prueba (fraudes y correos legítimos).
├── .streamlit/
│   ├── config.toml             Paleta de colores de la aplicación.
│   └── secrets.toml.example    Plantilla para la clave de API.
├── requirements.txt            Dependencias de Python.
└── README.md
```

La lógica está separada de la interfaz: `app.py` no sabe nada de Gemini, solo
llama a las funciones del paquete `guardia/`. Cambiar de proveedor de IA
implicaría reescribir `analisis.py` y ningún otro archivo.

## Cómo ejecutarlo localmente

```bash
git clone https://github.com/cubi20/guardia.git
cd guardia
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Conseguí una clave gratuita en [Google AI Studio](https://aistudio.google.com/apikey)
y cargala (nunca se escribe en el código):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# editá el archivo y pegá tu clave
```

Y levantá la aplicación:

```bash
streamlit run app.py
```

## Despliegue en Streamlit Community Cloud

1. Subí el repositorio a GitHub (público).
2. Entrá a [share.streamlit.io](https://share.streamlit.io) → **Create app** →
   elegí el repo, la rama `main` y el archivo `app.py`.
3. En **Advanced settings → Secrets**, pegá:
   ```toml
   GEMINI_API_KEY = "AIza..."
   ```
4. **Deploy**.

## Factibilidad económica

**El costo de operación es cero.** El nivel gratuito de la API de Gemini cubre
holgadamente el uso previsto de la herramienta y el hosting en Streamlit
Community Cloud tampoco tiene costo: no hace falta tarjeta de crédito para poner
la aplicación en producción.

Como referencia de escalabilidad, cada análisis consume alrededor de 1.500
tokens de entrada y 500 de salida:

| Concepto | Nivel gratuito | Equivalente en nivel pago |
|---|---|---|
| Un análisis (`gemini-2.5-flash`) | US$ 0 | ≈ US$ 0,0017 |
| 500 análisis por mes | US$ 0 | ≈ US$ 0,85 |
| 5.000 análisis por mes | US$ 0 | ≈ US$ 8,50 |
| Hosting (Streamlit Community Cloud) | US$ 0 | US$ 0 |
| Repositorio (GitHub) y entorno (Python, VS Code) | US$ 0 | US$ 0 |

Precios del nivel pago vigentes en agosto de 2026: US$ 0,30 por millón de tokens
de entrada y US$ 2,50 por millón de salida para `gemini-2.5-flash`. La
aplicación **mide los tokens realmente consumidos** en cada consulta y muestra su
costo equivalente en la barra lateral.

## Limitaciones

- **GuardIA es un asistente, no un veredicto final.** El modelo puede
  equivocarse en ambos sentidos: marcar un correo legítimo como sospechoso o
  dejar pasar uno malicioso. Por eso siempre recomienda verificar por un canal
  oficial.
- **Analiza texto, no archivos.** No abre adjuntos ni sigue enlaces.
- **No reemplaza** al antivirus, a los filtros de correo ni al segundo factor de
  autenticación (MFA): los complementa en el punto donde esas defensas no
  llegan, que es la decisión de la persona.
- **Privacidad:** el texto se envía a la API de Google Gemini. No debe pegarse
  información confidencial innecesaria; en un uso productivo correspondería
  anonimizar los datos sensibles.
- **El nivel gratuito tiene cupos** de consultas por minuto y por día. Son
  holgados para el uso de una PyME, pero un pico de tráfico podría agotarlos
  temporalmente.
- **El phishing evoluciona:** el prompt y los ejemplos deben mantenerse
  actualizados para no perder efectividad.

## Trabajo futuro

La próxima función prevista es la **placa de concientización**: una pieza visual
generada con un modelo texto → imagen a partir del diagnóstico, para que el
responsable de la PyME pueda compartirla por el grupo interno y convertir cada
intento de phishing recibido en material de capacitación para todo el equipo.
Quedó fuera de esta versión porque la generación de imágenes no está disponible
en los niveles gratuitos, y mantener la herramienta sin costo es parte de su
propuesta de valor.

## Decisiones de diseño del prompt

| Decisión | Por qué |
|---|---|
| Rol de *analista de ciberseguridad experto* | Sitúa al modelo en el dominio correcto y mejora la precisión de las señales que detecta. |
| Checklist explícito de qué evaluar | Reduce la ambigüedad y hace que dos análisis del mismo correo sean consistentes. |
| Salida dirigida con esquema | La interfaz siempre recibe la misma estructura; no hay que parsear texto libre. |
| `propertyOrdering`: señales antes que explicación | El modelo redacta apoyándose en lo que ya detectó, no al revés. |
| Reglas anti-alucinación | Le prohíben inventar datos y afirmar con certeza absoluta. |
| Lenguaje simple obligatorio | El destinatario es un empleado sin perfil técnico. |
| Delimitadores `<<<MENSAJE>>>` | Protegen contra inyección de prompt: si el correo contiene órdenes dirigidas a una IA, se tratan como una señal de riesgo, no como instrucciones. |
| Temperatura 0.2 | Buscamos un diagnóstico estable y reproducible, no creatividad. |

---

**Tecnologías:** Python · Streamlit · API de Google Gemini (salida dirigida con
esquema) · Streamlit Community Cloud · GitHub
