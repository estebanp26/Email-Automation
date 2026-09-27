# ============================================================
# Tablero HSE — React + Vite
# ------------------------------------------------------------
# Descripción:
#   Imagen de desarrollo para probar el tablero contra la API
#   puente con `docker compose up --build`. Expone Vite en el
#   puerto 5173 y redirige /api hacia el servicio api.
# ============================================================
FROM node:20-alpine

WORKDIR /codigo

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
