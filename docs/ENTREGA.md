# Checklist de entrega — Proyecto Final GuardIA

Lo que ya está hecho y lo que falta que hagas vos (necesita tus cuentas).

> **Nota:** el proyecto usa la API de **Google Gemini**, cuyo nivel gratuito no
> requiere tarjeta de crédito. La pre-entrega mencionaba OpenAI; el cambio está
> explicado y justificado en la lámina 12 de la presentación.

---

## ✅ Ya está listo

- [x] Aplicación web con Streamlit: título, descripción, botón de acción y sección "Cómo funciona".
- [x] Integración de IA con **salida dirigida** sobre `gemini-2.5-flash`.
- [x] Costo de operación cero: nivel gratuito de la API + hosting sin cargo.
- [x] Estructura visual: header, footer, paleta de colores propia.
- [x] Código organizado y comentado, con la lógica separada de la interfaz.
- [x] Repositorio git inicializado con el primer commit.
- [x] Presentación de documentación: `docs/GuardIA-ProyectoFinal-IdoyagaMolina.pptx`.

---

## 1. Conseguir la clave de Gemini y probar la app (10 minutos)

La clave es **gratuita y no pide tarjeta de crédito**:

1. Entrá a [aistudio.google.com/apikey](https://aistudio.google.com/apikey) con tu cuenta de Google.
2. **Create API key** → copiala.
3. Abrí `.streamlit/secrets.toml` y pegala en la línea `GEMINI_API_KEY = ""`.

Después:

```bash
cd "/Users/agustin/Documents/Coder House/GuardIA" && ./venv/bin/python -m streamlit run app.py
```

Probá los cinco ejemplos del selector. Los tres primeros deberían dar riesgo
**alto**, el del turno médico **bajo** y el del paquete retenido **medio**. Si
alguno no coincide, el prompt está en `guardia/prompts.py` y se puede ajustar.

Fijate también en la barra lateral: muestra los tokens consumidos y el costo
equivalente en el nivel pago. Es la evidencia de la factibilidad económica.

---

## 2. Subir el código a GitHub

Creá un repositorio **público** vacío en GitHub llamado `guardia` (sin README,
sin .gitignore) y después:

```bash
cd "/Users/agustin/Documents/Coder House/GuardIA" && git remote add origin https://github.com/TU-USUARIO/guardia.git && git push -u origin main
```

> El archivo `.streamlit/secrets.toml` está en `.gitignore`: tu clave **no** se
> sube. Verificalo con `git status` antes de pushear.

---

## 3. Desplegar en Streamlit Community Cloud

1. Entrá a [share.streamlit.io](https://share.streamlit.io) con tu cuenta (usuario `cubi20`).
2. **Create app** → **Deploy a public app from GitHub**.
3. Repositorio: `TU-USUARIO/guardia` · Rama: `main` · Archivo: `app.py`.
4. **Advanced settings → Secrets**, pegá:

   ```toml
   GEMINI_API_KEY = "AIza..."
   ```

5. **Deploy**. Tarda unos minutos la primera vez.
6. Cuando cargue, probá un ejemplo para confirmar que la clave quedó bien.

Guardá la URL: va a ser algo como `https://guardia.streamlit.app`.

---

## 4. Completar los enlaces en la presentación

Abrí `docs/GuardIA-ProyectoFinal-IdoyagaMolina.pptx` y andá a la **lámina 15
("Enlaces del proyecto")**. Reemplazá las tres direcciones de ejemplo por:

| Campo | Qué poner |
|---|---|
| Aplicación desplegada | La URL real de Streamlit del paso 3 |
| Código fuente | La URL real del repositorio de GitHub del paso 2 |
| Demostración | El enlace al video, o borrá esa tarjeta si no vas a grabarlo |

Después borrá la línea roja de advertencia que está debajo de las tarjetas.

Actualizá también la línea **"App en línea"** al principio del `README.md` del
repositorio, y volvé a pushear.

---

## 5. Mejorar las capturas (opcional pero recomendado)

Las capturas de las láminas 7 y 8 son de la app corriendo en local y **sin
resultado de análisis a la vista**. Una vez desplegada, sacá una captura de un
análisis real (con el nivel de riesgo, las señales y la recomendación) y
reemplazá la de la lámina 7: es la imagen que mejor muestra que la app funciona.

---

## 6. Pasar la presentación a Google Slides y compartirla

La consigna pide el documento en **Google Presentaciones con permiso de
Comentador**:

1. Entrá a [drive.google.com](https://drive.google.com) → **Nuevo → Subir archivo** →
   elegí `GuardIA-ProyectoFinal-IdoyagaMolina.pptx`.
2. Clic derecho sobre el archivo → **Abrir con → Presentaciones de Google**.
3. **Archivo → Guardar como Presentaciones de Google** (queda una copia nativa).
4. Revisá que las láminas se vean bien: Google Slides a veces mueve algún texto.
   Prestá atención a las láminas 9, 10, 11 y 13, que tienen bloques de código y tablas.
5. **Compartir → Acceso general → Cualquier persona con el enlace → Comentador**.
6. **Copiar enlace** y entregá ese enlace.

---

## 7. Antes de entregar, revisá

- [ ] La app abre desde el enlace de Streamlit y analiza un correo de prueba.
- [ ] El repositorio de GitHub es público y **no** contiene la clave de API.
- [ ] Las tres direcciones de la lámina 15 son las reales.
- [ ] El enlace de Google Slides está en modo **Comentador**.
- [ ] Los datos de la portada están bien (nombre, comisión #95920).
