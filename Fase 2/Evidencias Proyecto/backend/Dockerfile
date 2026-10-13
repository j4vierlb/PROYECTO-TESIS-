# =============================================================================
# Dockerfile del backend (FastAPI)
# -----------------------------------------------------------------------------
# Receta para construir la "imagen" del backend: un Linux mínimo con Python,
# las librerías de requirements.txt y el código de app/. Lo usa
# docker-compose.yml (servicio "backend").
# =============================================================================

FROM python:3.12-slim

# No generar archivos .pyc y mostrar los logs al instante.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero solo requirements.txt: así Docker reutiliza esta capa (ya con las
# librerías instaladas) mientras no cambien las dependencias, aunque cambie
# el código. Reconstruir queda mucho más rápido.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# El servidor no corre como administrador (root) del contenedor.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# --host 0.0.0.0: escucha fuera del contenedor (sin esto, nadie lo alcanza).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
