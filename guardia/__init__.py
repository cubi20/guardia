"""
GuardIA — Asistente anti-phishing con IA para PyMEs.

Paquete con la lógica de negocio de la aplicación, separada de la interfaz
(app.py) para que el código sea más fácil de leer, probar y mantener.

Módulos:
    prompts.py   Prompts y esquema de salida dirigida (JSON Schema).
    analisis.py  Cliente de OpenAI, análisis texto-texto y cálculo de costos.
    imagen.py    Generación de la placa de concientización (texto-imagen).
    ejemplos.py  Mensajes de ejemplo para probar la aplicación.
"""

__version__ = "1.0.0"
__author__ = "Agustín Idoyaga Molina"
