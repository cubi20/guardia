# 🛡️ GuardIA — Asistente anti-phishing con IA para PyMEs

> Proyecto Final · **Prompt Engineering para Programadores** — Diplomatura en Inteligencia Artificial, CoderHouse
> Estudiante: **Agustín Idoyaga Molina** · Comisión **#95920**

GuardIA es una aplicación web donde cualquier empleado pega un correo o mensaje
sospechoso y, en segundos, recibe un diagnóstico claro: **qué tan riesgoso es,
qué señales concretas se detectaron, una explicación en lenguaje simple y qué
hacer al respecto**.

🔗 **App en línea:** _(completar con el enlace de Streamlit Community Cloud)_

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

Además, GuardIA puede generar una **placa de concientización** con IA a partir
del resultado, para que cada intento de phishing recibido se transforme en
material de capacitación para todo el equipo.

## Los dos modelos de IA que integra

| Modelo | Rol en la aplicación |
|---|---|
| **Texto → texto** (`gpt-4o-mini`) | Núcleo de la app. Analiza el mensaje y devuelve el diagnóstico con **salida dirigida** (*Structured Outputs*). |
| **Texto → imagen** (`gpt-image-1-mini` / `gpt-image-1` / `dall-e-3`) | Genera la ilustración de la placa de concientización a partir del diagnóstico. |

### Salida dirigida

En lugar de pedirle al modelo "respondeme en JSON" y confiar en que obedezca, se
envía un **JSON Schema con `strict: true`**: la API valida la respuesta contra el
esquema antes de devolverla. Así la interfaz siempre recibe la misma estructura
y puede dibujarla igual en todos los casos, sin parsear texto libre.

```json
{
  "nivel_riesgo": "bajo | medio | alto | indeterminado",
  "puntaje": 0-100,
  "tipo_de_engano": "técnica detectada",
  "senales": [{"titulo": "...", "detalle": "...", "gravedad": "baja|media|alta"}],
  "explicacion": "en lenguaje simple, no técnico",
  "recomendacion": "qué hacer ahora",
  "verificacion_sugerida": "cómo confirmarlo por un canal oficial"
}
```

## Estructura del proyecto

```
GuardIA/
├── app.py                      Interfaz web (Streamlit): header, formulario,
│                               resultado, "cómo funciona" y footer.
├── guardia/
│   ├── __init__.py
│   ├── prompts.py              Prompt principal, JSON Schema y prompt de imagen.
│   ├── analisis.py             Cliente de OpenAI, análisis y cálculo de costos.
│   ├── imagen.py               Placa de concientización (texto → imagen + Pillow).
│   └── ejemplos.py             Mensajes de prueba (fraudes y correos legítimos).
├── .streamlit/
│   ├── config.toml             Paleta de colores de la aplicación.
│   └── secrets.toml.example    Plantilla para la clave de API.
├── requirements.txt            Dependencias de Python.
├── packages.txt                Tipografías para el despliegue en Streamlit Cloud.
└── README.md
```

La lógica está separada de la interfaz: `app.py` no sabe nada de OpenAI, solo
llama a las funciones del paquete `guardia/`.

## Cómo ejecutarlo localmente

```bash
git clone https://github.com/<tu-usuario>/guardia.git
cd guardia
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Cargá tu clave de OpenAI (nunca se escribe en el código):

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
   OPENAI_API_KEY = "sk-proj-..."
   ```
4. **Deploy**. El archivo `packages.txt` instala la tipografía DejaVu que usa la
   placa de concientización.

## Factibilidad económica

Cada análisis consume alrededor de 1.500 tokens de entrada y 500 de salida.

| Concepto | Costo |
|---|---|
| Un análisis (`gpt-4o-mini`) | ≈ US$ 0,00053 |
| 500 análisis por mes | ≈ US$ 0,27 |
| 5.000 análisis por mes | ≈ US$ 2,65 |
| Placa de concientización (opcional, a pedido) | ≈ US$ 0,01 |
| Hosting (Streamlit Community Cloud) | US$ 0 |
| Repositorio (GitHub) y entorno (Python, VS Code) | US$ 0 |

Precios de OpenAI vigentes en agosto de 2026: US$ 0,15 por millón de tokens de
entrada y US$ 0,60 por millón de salida para `gpt-4o-mini`. La aplicación
**calcula y muestra el costo real** de cada consulta en la barra lateral, a
partir de los tokens efectivamente consumidos.

## Limitaciones

- **GuardIA es un asistente, no un veredicto final.** El modelo puede
  equivocarse en ambos sentidos: marcar un correo legítimo como sospechoso o
  dejar pasar uno malicioso. Por eso siempre recomienda verificar por un canal
  oficial.
- **Analiza texto, no archivos.** No abre adjuntos ni sigue enlaces.
- **No reemplaza** al antivirus, a los filtros de correo ni al segundo factor de
  autenticación (MFA): los complementa en el punto donde esas defensas no
  llegan, que es la decisión de la persona.
- **Privacidad:** el texto se envía a la API de OpenAI. No debe pegarse
  información confidencial innecesaria; en un uso productivo correspondería
  anonimizar los datos sensibles.
- **El phishing evoluciona:** el prompt y los ejemplos deben mantenerse
  actualizados para no perder efectividad.

## Decisiones de diseño del prompt

| Decisión | Por qué |
|---|---|
| Rol de *analista de ciberseguridad experto* | Sitúa al modelo en el dominio correcto y mejora la precisión de las señales que detecta. |
| Checklist explícito de qué evaluar | Reduce la ambigüedad y hace que dos análisis del mismo correo sean consistentes. |
| Salida dirigida con JSON Schema `strict` | La interfaz siempre recibe la misma estructura; no hay que parsear texto libre. |
| Reglas anti-alucinación | Le prohíben inventar datos y afirmar con certeza absoluta. |
| Lenguaje simple obligatorio | El destinatario es un empleado sin perfil técnico. |
| Delimitadores `<<<MENSAJE>>>` | Protegen contra inyección de prompt: si el correo contiene órdenes dirigidas a una IA, se tratan como una señal de riesgo, no como instrucciones. |
| Temperatura 0.2 | Buscamos un diagnóstico estable y reproducible, no creatividad. |

---

**Tecnologías:** Python · Streamlit · API de OpenAI (Structured Outputs) ·
Pillow · Streamlit Community Cloud · GitHub
