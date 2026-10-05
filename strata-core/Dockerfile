# ============================================================
# Riwi HSE — Strata Core (Motor de Percepción, OCR e IA)
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_THREAD_LIMIT=1 \
    OMP_NUM_THREADS=1

WORKDIR /app

# Instalar dependencias de sistema: Tesseract OCR (spa + eng), librerías gráficas para PyMuPDF y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del motor
COPY . ./

# Crear usuario sin privilegios para ejecución segura
RUN adduser --disabled-password --gecos "" hseuser \
    && chown -R hseuser:hseuser /app
USER hseuser

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
