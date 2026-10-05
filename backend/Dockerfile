# ============================================================
# Riwi HSE Attendance & Justification — Backend API (FastAPI)
# ============================================================
FROM python:3.12-slim

# Evitar generación de .pyc y habilitar buffering inmediato de logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema para compilación y soporte PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY app/ ./app/

# Crear y cambiar a usuario sin privilegios para ejecución segura
RUN adduser --disabled-password --gecos "" hseuser \
    && chown -R hseuser:hseuser /app
USER hseuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
