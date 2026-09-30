# =============================================================================
# Dockerfile del panel web (React + Vite, servido con nginx)
# -----------------------------------------------------------------------------
# Tiene dos etapas:
#   1. "build": usa Node para compilar React y generar archivos estáticos
#      (HTML, CSS y JavaScript) en la carpeta dist/.
#   2. nginx: un servidor web liviano que solo entrega esos archivos.
# La imagen final lleva solo nginx + dist/, sin Node ni node_modules.
# =============================================================================

# ---------- Etapa 1: compilar ----------
FROM node:22-alpine AS build
WORKDIR /app

# Primero las dependencias (se reutilizan mientras no cambie package-lock.json).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Dirección del backend que usará el navegador. Vite la escribe DENTRO del
# JavaScript al compilar, por eso llega como argumento de compilación.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- Etapa 2: servir ----------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
