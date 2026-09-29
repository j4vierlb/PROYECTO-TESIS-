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
