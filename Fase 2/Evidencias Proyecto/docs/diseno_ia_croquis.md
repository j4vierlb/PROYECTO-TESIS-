# Diseño de la IA del croquis (borrador v0.1)

Objetivo: que la IA **proponga** dónde poner las trampas de un cliente y el operador, en terreno, las **confirme, mueva o retire** desde la app. La IA nunca deja un croquis como definitivo.

Lo que ya existe y se reutiliza:

- Tablas `croquis` (`sugerido_por_ia`, `validado_por_operador`, `version`, `imagen_satelital_url`) y `dispositivos_trampa` (`tipo`, `ubicacion`, `sugerido_por_ia`, `confirmado`, `estado`) en [`schema.sql`](../database/schema.sql).
- `GET /croquis/{visita_id}` y `PATCH /dispositivos-trampa/{id}` (confirmar / mover / eliminar).
- El mismo patrón que el agente de WhatsApp: la IA devuelve JSON, el backend lo valida antes de guardar nada.

## 1. Qué recibe

| Dato | De dónde sale | Obligatorio |
|---|---|---|
| Coordenadas del predio (`lat`, `lng`) | `clientes.ubicacion` (geocodificando `clientes.direccion` si está vacía) | Sí |
| Imagen satelital del predio, 640×640 px, zoom 19–20 | API de mapas estáticos (Google Static Maps o Mapbox); se guarda la URL en `croquis.imagen_satelital_url` | Sí |
| Límites geográficos de la imagen (esquinas N/S/E/O) | Se calculan en el backend a partir del centro y el zoom | Sí (no va a la IA, sirve para convertir) |
| Tipo de recinto | Lo indica el operador o el panel: casa, restaurante, bodega, local comercial, industria | Sí |
| Plaga objetivo | roedores, cucarachas, moscas, otra | Sí |
| Superficie aproximada (m²) y n° de accesos | Operador / panel | No |
| Croquis anterior del cliente | Última versión en `croquis` + sus `dispositivos_trampa` con `estado` (`activo`, `revisar`, `retirado`) | No (solo si hay) |
| Notas del operador | Texto libre ("hay un desagüe en el patio trasero") | No |

## 2. Qué propone

La IA responde un JSON. Las posiciones van en **píxeles de la imagen**, no en lat/lng: un modelo de lenguaje ubica mucho mejor "dónde en la foto" que coordenadas con 6 decimales. El backend convierte píxel → lat/lng con los límites de la imagen.

```json
{
  "resumen": "Casa con patio trasero; foco en perímetro y zona de basura.",
  "dispositivos": [
    {
      "tipo": "cebadero",
      "x": 412, "y": 233,
      "zona": "perímetro norte, junto al muro",
      "motivo": "Muro medianero con vegetación: ruta habitual de roedores.",
      "confianza": 0.7
    }
  ],
  "advertencias": ["La imagen no permite ver el interior de la bodega."]
}
```

- `tipo` ∈ `cebadero`, `trampa_pegamento`, `trampa_luz`, `otro` (los mismos del `CHECK` de la tabla).
- `confianza` 0–1: la app puede resaltar en otro color las de baja confianza para que el operador las revise primero.
- `motivo` y `zona` se muestran al operador; ayudan a que confíe (o no) en la sugerencia.

## 3. Validaciones del backend (antes de guardar)

1. JSON válido y `tipo` dentro de los permitidos; si no, se descarta ese dispositivo.
2. `x`, `y` dentro de 0–640.
3. Tras convertir a lat/lng, el punto debe quedar a ≤ 60 m del centro del predio (`ST_DWithin`).
4. Separación mínima de 3 m entre dispositivos (se descarta el duplicado).
5. Máximo de dispositivos según superficie (ej. 1 cada 15 m de perímetro, tope 30).
6. Si la IA falla o no queda ningún dispositivo válido: **plan B por reglas** (cebaderos en las 4 esquinas + 1 cada 15 m de perímetro), marcado igual como `sugerido_por_ia = true` y con advertencia.

## 4. Qué se guarda

- Nuevo registro en `croquis` con `version = anterior + 1`, `sugerido_por_ia = true`, `validado_por_operador = false`.
- Cada dispositivo en `dispositivos_trampa` con `sugerido_por_ia = true`, `confirmado = false`, `codigo` correlativo (`T-01`, `T-02`, …).
- Si hay croquis anterior, las trampas `activo` se copian tal cual (confirmadas) y la IA solo propone las **nuevas** o sugiere retirar las `revisar`.

## 5. Endpoint propuesto

`POST /croquis/{visita_id}/sugerencia` (solo operador o coordinador de la empresa).

Body: `{ "tipo_recinto": "casa", "plaga": "roedores", "superficie_m2": 180, "notas": "..." }`

Respuesta: el mismo `CroquisResponse` de `GET /croquis/{visita_id}`, así la app no necesita una pantalla nueva para mostrarlo. El operador luego usa el `PATCH` que ya existe, y cuando termina se marca `validado_por_operador = true` (endpoint nuevo, pendiente).

## 6. Modelo y costo estimado

- `gpt-4.1-mini` con imagen (acepta entrada de imagen y `response_format: json_object`), igual que el agente de WhatsApp.
- Imagen 640×640 ≈ 650 tokens + prompt ≈ 600 + salida ≈ 600 (10–15 dispositivos con motivo).
- ≈ 1.250 × 0,40 + 600 × 1,60 por millón ≈ **0,0015 USD (~1,4 CLP) por croquis**, más el costo de la imagen satelital del proveedor de mapas.
- Verificar con `usage` en las primeras pruebas.

## 7. Preguntas abiertas para el equipo

1. ¿Proveedor de imagen satelital? Google Static Maps (mejor imagen en Santiago, requiere tarjeta) vs Mapbox (cuota gratis mayor).
2. ¿Kill Bichos tiene una norma interna de distancia entre cebaderos? Si la hay, reemplaza el "1 cada 15 m".
3. ¿Quién completa tipo de recinto y plaga: el agente de WhatsApp al agendar, el panel, o el operador al llegar?
4. ¿La sugerencia se genera al agendar (antes de la visita) o al abrir el croquis en terreno? Generarla antes permite que el operador la vea camino al cliente.
5. Sin señal en terreno: la app ya tiene base local; ¿se descarga la sugerencia junto con la agenda del día?

## 8. Siguientes pasos

1. Responder las preguntas abiertas.
2. Probar el prompt a mano con 3–5 imágenes reales de clientes de Macul y comparar con croquis hechos por un técnico.
3. Implementar `app/ai/croquis_agent.py` + el endpoint, con el plan B por reglas desde el inicio.
