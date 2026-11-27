# Despliegue con HTTPS (servidor en la nube)

Esta carpeta guarda la configuración que agrega HTTPS al sistema en el servidor. Son dos archivos pequeños y no contienen claves:

- `Caddyfile`: le dice a Caddy qué dirección pública va a cada servicio. El panel sale por `killbichos-panel.duckdns.org` y la API, por `killbichos-api.duckdns.org`.
- `docker-compose.https.yml`: agrega el servicio `caddy` al `docker-compose.yml` de la raíz. Caddy abre los puertos 80 y 443, pide solo el certificado y lo renueva solo.

## Por qué no están en la raíz

Un archivo llamado `docker-compose.override.yml` en la raíz lo carga `docker compose` automáticamente. Así, cualquiera que levante el proyecto en su computador abriría los puertos 80 y 443 sin querer. Por eso viven aquí y se activan solo a propósito.

## Cómo se usa

Desde la raíz del repositorio, en el servidor:

```bash
docker compose -f docker-compose.yml -f "Fase 3/Evidencias Grupales/deploy/docker-compose.https.yml" up -d --build
```

Requisitos:

- Los dos nombres de DuckDNS deben apuntar a la IP del servidor.
- El cortafuegos debe dejar abiertos los puertos 22, 80 y 443. El resto, incluida la base de datos, queda cerrado.
- Las claves van solo en el `.env` del servidor, que no se sube a git.

## Cómo se actualiza el servidor

```bash
# 1. Guardar los registros del backend: al reconstruir, el contenedor se recrea y se pierden.
mkdir -p ~/logs_antes_deploy
docker compose logs -t backend > ~/logs_antes_deploy/backend_$(date +%Y-%m-%d_%H%M).log

# 2. Traer los cambios y reconstruir.
git pull --ff-only
docker compose up -d --build backend web
```

## Estado de esta carpeta

Estos archivos son una copia de los que corren hoy en el servidor. Allá siguen con los nombres `Caddyfile` y `docker-compose.override.yml`, en la raíz del clon, y no están en git. La forma de arrancar con `-f` y la carpeta `deploy/` es la que se documenta aquí, y **todavía no se probó en el servidor**.

El servidor también mantiene el túnel ngrok encendido para el webhook de Twilio.
