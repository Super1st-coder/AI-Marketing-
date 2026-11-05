# webhooks/_shared/

Módulos **fuente de verdad** compartidos entre el `webhook-router` y las
Cloud Functions procesadoras.

> [!NOTE]
> Cloud Functions no comparten código automáticamente — cada CF necesita sus
> propios archivos en su directorio de source. Esta carpeta es el **origen**;
> el `Makefile` de cada CF es responsable de copiar lo necesario antes del deploy.

## Módulos

| Archivo | Descripción | Usado en |
|---------|-------------|----------|
| `verifiers.py` | Verificadores HMAC-SHA256, SHA-512, Stripe | `router/` |
| `registry.py` | `SERVICE_REGISTRY` — mapa servicio→config | `router/` |

## Agregar código compartido

Si una lógica necesita estar en el `router` **y** en un procesador:

1. Escríbela aquí en `_shared/`
2. Agrégala al paso de build/deploy de ambas CFs:

```makefile
# En webhooks/router/Makefile
pre-deploy:
    cp ../_shared/verifiers.py .
    cp ../_shared/registry.py .
```

## Convención de nombres de recursos GCP

| Recurso | Patrón | Ejemplo |
|---------|--------|---------|
| Pub/Sub topic | `wh-{servicio}-{entorno}` | `wh-appsflyer-prd` |
| CF procesadora | `wh-proc-{servicio}` | `wh-proc-appsflyer` |
| Secret de firma | `wh-secret-{servicio}` | `wh-secret-appsflyer` |
| CF router | `webhook-router` | único, sin entorno |
| API Gateway | `hiluca-webhook-gateway` | único |
| API Config | `webhook-gateway-config-v{N}` | incrementar en cada deploy |

## Agregar un nuevo proveedor — Checklist

```
[ ] Agregar entrada en _shared/registry.py (y copiar a router/)
[ ] Crear secret en Secret Manager: wh-secret-{servicio}
[ ] Crear topics Pub/Sub: wh-{servicio}-dev  y  wh-{servicio}-prd
[ ] Crear webhooks/{servicio}/processor/main.py
[ ] Crear webhooks/{servicio}/processor/requirements.txt
[ ] Deploy CF procesadora: wh-proc-{servicio}
[ ] Crear suscripción Pub/Sub → CF procesadora
[ ] Redeploy webhook-router (para recargar registry.py)
[ ] Actualizar gateway/api-config.yaml si el proveedor necesita headers especiales
[ ] Probar con entorno=dev (sin firma) y luego entorno=prd (con firma real)
```
