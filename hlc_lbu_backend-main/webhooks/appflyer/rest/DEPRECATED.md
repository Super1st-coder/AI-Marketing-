# ⚠️ DEPRECATED — webhooks/appflyer/rest/

Esta Cloud Function (`appflyer-webhook`) fue el punto de entrada original
para los webhooks de AppsFlyer en `integrate.hiluca.com/`.

## Reemplazada por

**`webhooks/router/`** — CF universal `webhook-router` que maneja todos
los servicios bajo la URL estructurada:

```
https://integrate.hiluca.com/webhook/{servicio}/{version}/{entorno}
https://integrate.hiluca.com/webhook/appsflyer/v1.0.0/prd
```

## Qué hacía esta CF

- Recibía GET y POST en la raíz `/`
- Publicaba el payload crudo en el topic Pub/Sub `appflyer-events`
- **Sin validación de firma**

## Qué hace ahora el router

- Ruta estructurada con servicio + versión + entorno
- Validación HMAC-SHA256 por proveedor (cargado de Secret Manager)
- Genera `idempotency_key` por evento
- Publica en topic `wh-appsflyer-{entorno}` con atributos de trazabilidad

## Estado

Mantener esta carpeta como referencia histórica.
No hacer nuevos deploys de `appflyer-webhook`.
El procesador `appflyer/processor/` sigue activo y fue adaptado
para el nuevo formato de mensajes.
