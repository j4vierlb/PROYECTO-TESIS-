# Panel web Kill Bichos

Panel operativo para administrar clientes y agendar visitas por operador.

## Ejecución

Con el backend corriendo en `http://localhost:8000`:

```bash
npm install
npm run dev
```

La URL de la API se puede cambiar con `VITE_API_URL`.

El panel utiliza el usuario de prueba `admin@killbichos.cl` con clave `demo1234`.

## Alcance

- Login para usuarios administrativos (`admin` y `coordinador`).
- Agenda filtrable por día y operador.
- Creación y actualización del estado de visitas.
- CRUD de clientes con coordenadas del predio.
- Resumen de clientes, visitas del día y visitas pendientes.

## Fechas y datos opcionales

La agenda muestra `America/Santiago`, incluyendo horario de verano e invierno.
El formulario interpreta la hora elegida como hora de Chile y la envía en UTC
con sufijo `Z`, como exige el contrato de la API. Una hora inexistente por el
cambio de horario se rechaza con un mensaje antes de enviar la solicitud.

`Sin asignar` envía `operador_id: null`. Los clientes que llegan desde WhatsApp
sin ubicación se muestran como `Sin coordenadas` y se pueden editar sin inventar
una ubicación. En la creación manual siguen siendo obligatorias las coordenadas,
según el contrato actual del backend; al editar se pueden dejar ambas vacías.

## Pruebas

Desde esta carpeta:

```bash
npm ci
npm test
npm run build
```

Las pruebas de React simulan las respuestas HTTP; no conectan una base real.
Los casos, resultados, capturas y pasos para probar con PostGIS real están en
[`../pruebas/Panel_regresion_2026-10-09.md`](../pruebas/Panel_regresion_2026-10-09.md).
