"""
GuardIA — Asistente anti-phishing con IA para PyMEs.

Paquete con la lógica de negocio de la aplicación, separada de la interfaz
(app.py) para que el código sea más fácil de leer, probar y mantener.

Módulos:
    prompts.py   Prompt principal y esquema de la salida dirigida.
    analisis.py  Cliente de Gemini, análisis del mensaje y medición del consumo.
    ejemplos.py  Mensajes de ejemplo para probar la aplicación.
"""

__version__ = "1.0.0"
__author__ = "Agustín Idoyaga Molina"
