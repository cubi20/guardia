# 🛡️ GuardIA — Asistente anti-phishing con IA para PyMEs

> **Diplomatura en Inteligencia Artificial — CoderHouse**
> Curso: *Inteligencia artificial: Generación de Prompts* · Comisión **#95920**
> Estudiante: **Agustín Idoyaga Molina**

Una aplicación web donde cualquier empleado pega un correo o mensaje sospechoso y recibe,
en segundos, un diagnóstico claro: qué tan riesgoso es, qué señales concretas se
detectaron, una explicación en lenguaje simple y una recomendación de qué hacer.

## Contenido del repositorio

Este repositorio reúne todo el proyecto a lo largo del cursado. Según qué estés buscando:

| Entregable | Dónde está |
|---|---|
| 🔗 **Aplicación desplegada** | https://guardia-iayvrupcyvzqzibgemf7l7.streamlit.app |
| 💻 **Código fuente de la app** | [`app.py`](app.py) y el paquete [`guardia/`](guardia/) |
| 📓 **Prueba de concepto — Fast Prompting** | [`notebooks/GuardIA_FastPrompting.ipynb`](notebooks/GuardIA_FastPrompting.ipynb) · [versión PDF](docs/GuardIA-Preentrega2-Notebook.pdf) |
| 📊 **Presentación del Proyecto Final** | [`docs/GuardIA-ProyectoFinal-IdoyagaMolina.pptx`](docs/) |
| 🎬 **Video demostrativo** | [`docs/guardia-demo.mp4`](docs/guardia-demo.mp4) |

El historial de commits documenta cómo evolucionó el proyecto y por qué se tomó cada
decisión técnica, incluidos los problemas que aparecieron al probarlo contra la API real.

La documentación que sigue describe el proyecto completo: el problema, la propuesta, la
viabilidad, la metodología, las herramientas y la implementación.

---

## 1. Introducción

### 1.1 Nombre del proyecto

**GuardIA** — de *guardia*, quien vigila y avisa, e *IA*.

Una aplicación web donde cualquier empleado pega un correo o mensaje sospechoso y recibe,
en segundos, un diagnóstico claro: qué tan riesgoso es, qué señales concretas se
detectaron, una explicación en lenguaje simple y una recomendación de qué hacer.

### 1.2 Presentación del problema a abordar

El phishing son correos o mensajes que se hacen pasar por una entidad confiable —un banco,
un proveedor, un cliente o incluso un compañero de trabajo— para que la persona haga clic
en un enlace, descargue un archivo o entregue sus credenciales.

**El problema no es tecnológico sino humano.** Por más filtros que tenga una empresa,
siempre hay un mensaje que llega a la bandeja de entrada y una persona que debe decidir, en
pocos segundos, si es legítimo o no. Los datos del *Verizon Data Breach Investigations
Report* (DBIR) 2025 lo dimensionan:

| Dato | Valor |
|---|---|
| Brechas de datos que involucran el factor humano | ~60% |
| Brechas en PyMEs que incluyen ransomware | 88% |
| Crecimiento del phishing en el último período | ≈ ×3 |

**Por qué esta problemática.** Afecta con especial dureza a las PyMEs, que son el eslabón
más débil: rara vez tienen equipo de seguridad, plan de capacitación o presupuesto para
herramientas comerciales, y sin embargo manejan datos de clientes, facturación y
transferencias. Un solo incidente puede paralizar su operación durante días. Además es una
problemática que conozco de cerca: curso la Licenciatura en Ciberseguridad y trabajo en el
área administrativa de una clínica, donde veo a diario circular correos con pedidos de
pagos, remitos y facturas.

**Por qué es relevante resolverla.** La IA generativa volvió el phishing mucho más
convincente: los mensajes fraudulentos ya no se detectan por su mala redacción. Si la IA
hizo más difícil el problema, tiene sentido usar esa misma tecnología para resolverlo. Y a
diferencia de una capacitación anual, que se olvida, una herramienta de consulta está
disponible siempre que aparece la duda.

### 1.3 Desarrollo de la propuesta de solución

La solución se apoya en un **modelo de lenguaje (texto → texto)** al que se le entrega el
mensaje sospechoso junto con un prompt especializado. El modelo lo evalúa y devuelve un
diagnóstico **estructurado**, que la aplicación siempre muestra de la misma manera.

El prompt hace tres cosas a la vez:

1. **Sitúa al modelo** en el rol de analista de ciberseguridad experto.
2. **Le da un checklist** de qué evaluar: remitente, urgencia, pedidos sensibles, enlaces,
   redacción y suplantación de autoridad.
3. **Le impone reglas** contra las alucinaciones: no inventar datos, no afirmar con certeza
   absoluta y recomendar siempre verificar por un canal oficial.

La respuesta se pide con **salida dirigida**: junto con la consulta se envía el esquema que
debe cumplir el JSON, y la API garantiza que lo cumpla.

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

El orden de los campos no es casual: `propertyOrdering` hace que el modelo detecte las
señales **antes** de puntuar y de redactar, de modo que el texto se apoye en lo que ya
identificó en lugar de justificar a posteriori.

### 1.4 Justificación de la viabilidad del proyecto

**Técnica.** Se apoya en herramientas que ya manejo y están disponibles gratis: Python con
Streamlit para la interfaz y la API de Gemini para el análisis. El alcance está acotado a
propósito: la app analiza texto pegado por el usuario, no se conecta al servidor de correo,
no requiere infraestructura propia ni base de datos, y no depende de permisos de
administrador en la empresa.

**Económica.** El nivel gratuito de la API da **20 consultas por día por modelo**; la app
encadena cuatro modelos, así que el cupo real ronda las 80 diarias, sin tarjeta de crédito.
El hosting en Streamlit Community Cloud tampoco cuesta nada. El notebook mide el consumo
real y proyecta el escalado.

**Recursos y tiempo.** Desarrollado en paralelo al cursado, sin hardware especial ni
licencias pagas: alcanza con una computadora y las cuentas gratuitas de Google AI Studio,
Streamlit y GitHub.

## 2. Objetivos

**General.** Poner el conocimiento de seguridad al alcance de quien no lo tiene, exactamente
en el momento en que necesita decidir si hacer clic.

**Específicos:**

1. Demostrar las técnicas de *fast prompting* aplicadas al problema: role prompting,
   checklist explícito, salida dirigida por esquema y control de alucinaciones.
2. Experimentar con distintas configuraciones de prompt y medir qué aporta cada una, en
   calidad del diagnóstico y en tokens.
3. Optimizar la cantidad de consultas a la API y cuantificar el ahorro.
4. Validar el prompt con casos reales, midiendo aciertos y falsos positivos.

## 3. Metodología

| Etapa | Qué se hace | Cómo se mide |
|---|---|---|
| **1. Línea de base** | Un prompt ingenuo, del tipo "decime si esto es phishing" | Si la salida es utilizable por un programa |
| **2. Refinamiento** | Se agregan rol, checklist y salida dirigida, de a una técnica por vez | Tokens, parseabilidad, calidad |
| **3. Optimización** | Una llamada estructurada contra encadenar varias | Consultas, tokens y costo por análisis |
| **4. Validación** | El prompt final sobre correos etiquetados | Aciertos, falsos positivos y negativos |

La regla que atraviesa todo: **cada mejora tiene que justificarse con un número.** Un prompt
más largo cuesta más tokens de entrada, así que solo vale la pena si el resultado lo paga.

## 4. Herramientas y tecnologías

| Herramienta | Para qué | Por qué esta |
|---|---|---|
| **Python 3** | Lenguaje del proyecto | Es el del SDK y del ecosistema |
| **Google Gemini** (familia Flash) | Modelo texto → texto | Nivel gratuito real y soporte de salida dirigida |
| **`google-genai`** | SDK oficial | Expone `response_schema`, la técnica central del proyecto |
| **Jupyter Notebook** | Prueba de concepto | Prompt, resultado y medición en un mismo lugar |
| **Streamlit** | Interfaz web | Interfaz funcional con pocas líneas, sin frontend aparte |
| **GitHub** | Control de versiones | El historial documenta cada ajuste y su porqué |

### Técnicas de prompting utilizadas

| Técnica | Cómo se aplica | Qué problema resuelve |
|---|---|---|
| **Role prompting** | "Sos un analista de ciberseguridad experto…" | Sitúa al modelo en el dominio correcto |
| **Checklist explícito** | Seis puntos a evaluar | Reduce la variabilidad entre análisis |
| **Salida dirigida** | Esquema enviado con la consulta | La app recibe siempre la misma estructura |
| **Ordenamiento de campos** | `propertyOrdering` | El modelo redacta apoyado en lo que ya detectó |
| **Reglas anti-alucinación** | "No inventes datos", "nunca afirmes con certeza absoluta" | Evita dominios y antecedentes inventados |
| **Delimitadores** | El mensaje va entre `<<<MENSAJE>>>` y `<<<FIN>>>` | Protege contra inyección de prompt |
| **Temperatura 0.2** | Configuración del modelo | Diagnóstico reproducible, no creativo |
| **Razonamiento acotado** | `thinking_level="LOW"` | Baja la latencia sin perder calidad |

## 5. Implementación

La prueba de concepto está en **[`notebooks/GuardIA_FastPrompting.ipynb`](notebooks/GuardIA_FastPrompting.ipynb)**,
con las salidas de una corrida real contra la API. Los hallazgos principales:

| Experimento | Resultado |
|---|---|
| **Evolución del prompt** (4 versiones) | Solo la versión con salida dirigida produce una respuesta que un programa puede usar — y además consume **menos** tokens en total, porque el modelo deja de escribir prosa |
| **Optimización de consultas** | **Una sola consulta** resuelve lo mismo que tres encadenadas, con menos tokens y sin respuestas que puedan contradecirse |
| **Nivel de razonamiento** | Mismo veredicto con razonamiento acotado, en una fracción del tiempo |
| **Validación** | **5 de 5** aciertos, **0 falsos positivos** sobre el correo legítimo |
| **Refinamiento** | El testing reveló que el manejo de las señales en un correo legítimo dependía de qué modelo respondiera: se fijó por prompt para que no quede librado al azar |
| **Inyección de prompt** | Un correo con órdenes dirigidas a la IA se clasifica como riesgo **alto**: las instrucciones se tratan como señal, no se ejecutan |

**Consultas a la API: una por mensaje analizado.** No por falta de alternativas, sino porque
se midió la alternativa y se descartó.

### Estructura del repositorio

```
GuardIA/
├── notebooks/
│   └── GuardIA_FastPrompting.ipynb   Prueba de concepto con los experimentos
├── app.py                            Interfaz web (Streamlit)
├── guardia/
│   ├── prompts.py                    Prompt principal y esquema de salida
│   ├── analisis.py                   Cliente de Gemini, análisis y consumo
│   └── ejemplos.py                   Correos de prueba
├── .streamlit/
│   ├── config.toml                   Paleta de colores
│   └── secrets.toml.example          Plantilla para la clave
├── docs/                             Presentación, capturas y video
└── requirements.txt
```

La lógica está separada de la interfaz: `app.py` no sabe nada de Gemini, solo llama a
funciones del paquete `guardia/`. Cambiar de proveedor implicaría reescribir `analisis.py` y
ningún otro archivo.

### Cómo ejecutarlo

```bash
git clone https://github.com/cubi20/guardia.git
cd guardia
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Conseguí una clave gratuita en [Google AI Studio](https://aistudio.google.com/apikey) y
cargala (nunca se escribe en el código):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```bash
streamlit run app.py
```

## 6. Limitaciones

- **GuardIA es un asistente, no un veredicto final.** El modelo puede equivocarse en ambas
  direcciones, así que siempre recomienda verificar por un canal oficial.
- **Analiza texto, no archivos.** No abre adjuntos ni sigue enlaces.
- **No reemplaza** al antivirus, a los filtros de correo ni al MFA: los complementa donde
  esas defensas no llegan, que es la decisión de la persona.
- **Privacidad:** el texto se envía a la API de Google Gemini. No debe pegarse información
  confidencial innecesaria.
- **El conjunto de prueba es chico y sintético.** Cinco correos alcanzan para justificar la
  factibilidad, no para afirmar una precisión general.
- **Cupo diario del nivel gratuito:** 20 consultas por modelo. La cascada lo multiplica,
  pero un pico de tráfico podría agotarlo.

## 7. Trabajo futuro

- **Placa de concientización** (texto → imagen) generada a partir del diagnóstico, para
  convertir cada intento de phishing en material de capacitación. Quedó fuera porque la
  generación de imágenes no está disponible en ningún nivel gratuito.
- **Conjunto de prueba más amplio**, con correos reales anonimizados de distintos rubros.
- **Few-shot prompting**: incorporar ejemplos resueltos dentro del prompt y medir si la
  mejora en consistencia justifica los tokens extra.
