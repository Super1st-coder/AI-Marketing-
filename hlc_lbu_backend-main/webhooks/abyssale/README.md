# webhook-abyssale-processor

Procesador de webhooks para Abyssale - Generación automática de imágenes.

## Descripción

Este servicio procesa webhooks provenientes de [Abyssale](https://www.abyssale.com/), una plataforma de generación automática de imágenes. Cuando Abyssale completa la generación de una imagen, envía un webhook que es recibido por el router universal, publicado en Pub/Sub, y finalmente procesado por esta Cloud Function.

El procesador decodifica el payload, extrae metadatos de routing, y realiza un POST a la API de HiLuca para integrar la imagen generada en el sistema.

## Flujo de Funcionamiento

1. **Webhook Entrante**: Abyssale envía un webhook a `https://integrate.hiluca.com/webhook/abyssale/v1.0.0/{entorno}`
2. **Verificación**: El router verifica la firma usando el método "abyssale" (basado en X-Referer header)
3. **Publicación**: El webhook verificado se publica en el topic Pub/Sub `wh-abyssale-{entorno}`
4. **Procesamiento**: Esta Cloud Function consume el mensaje, lo procesa y envía un POST a la API de HiLuca
5. **Integración**: La API de HiLuca recibe la información de la imagen generada

## Configuración del Router

El servicio está registrado en `webhooks/router/registry.py` con la siguiente configuración:

```python
"abyssale": {
    "v1.0.0": {
        "verifier": "abyssale",
        "secret_name": "wh-secret-abyssale",
        "signature_header": "X-Referer",
        "idempotency_field": "generation_request_id",
        "topic_pattern": "wh-abyssale-{entorno}",
    },
}
```

## URLs de Destino por Entorno

El procesador envía POST a las siguientes URLs según el entorno:

- **dev**: `https://api-dev.hiluca.com/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook`
- **qas**: `https://api-qa.hiluca.com/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook`
- **prd**: `https://api.hiluca.com/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook`

## Despliegue

### Prerrequisitos

- Proyecto GCP: `careful-acumen-422922-k4`
- gcloud CLI configurado
- Permisos para crear secrets, topics y Cloud Functions

### 1. Crear el Secret en Secret Manager

```bash
echo -n "tu_signing_secret_abyssale" | \
  gcloud secrets create wh-secret-abyssale \
    --data-file=- \
    --project=careful-acumen-422922-k4
```

**Nota**: Reemplaza `tu_signing_secret_abyssale` con el secret real proporcionado por Abyssale.

### 2. Crear los Topics Pub/Sub

```bash
gcloud pubsub topics create wh-abyssale-dev --project=careful-acumen-422922-k4
gcloud pubsub topics create wh-abyssale-qas --project=careful-acumen-422922-k4
gcloud pubsub topics create wh-abyssale-prd --project=careful-acumen-422922-k4
```

### 3. Desplegar la Cloud Function

```bash
gcloud functions deploy wh-proc-abyssale-{entorno} \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=./processor/ \
  --entry-point=pubsub_handler \
  --trigger-topic=wh-abyssale-{entorno} \
  --project=careful-acumen-422922-k4 \
  --memory=256MB \
  --timeout=60s \
  --max-instances=10 \
  --network=default \
  --subnet=default \
  --direct-vpc-egress=all \ 
  --network-tags=wh-proc-abyssale \
  --service-account=webhook-router-sa@careful-acumen-422922-k4.iam.gserviceaccount.com
```

**Nota**: Ajusta el `--trigger-topic` según el entorno (dev/qas/prd). Para múltiples entornos, despliega funciones separadas o usa un topic único con filtrado.

### 4. Configurar Abyssale

En el panel de Abyssale, configura el webhook para apuntar a:

```
https://integrate.hiluca.com/webhook/abyssale/v1.0.0/dev
```

Incluye el secret configurado en el paso 1 para la verificación de firma.

## Monitoreo

- **Logs**: Revisa los logs de Cloud Functions en GCP Console
- **Métricas**: Monitorea el uso de CPU/memoria y latencia
- **Alertas**: Configura alertas para errores de función o timeouts

## Desarrollo Local

Para probar localmente:

1. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Ejecuta la función localmente (requiere Functions Framework):
   ```bash
   functions-framework --target=pubsub_handler --signature-type=event
   ```

3. Envía un evento de prueba usando `curl` o herramientas como Postman.

## Dependencias

- `functions-framework`: Framework para Cloud Functions
- `google-cloud-logging`: Logging estructurado en GCP
- `requests`: Cliente HTTP para enviar POST a la API

## Notas de Seguridad

- Los secrets se almacenan en Secret Manager
- La comunicación usa HTTPS end-to-end
- Los webhooks incluyen verificación de firma para prevenir ataques
- Se implementa idempotency para evitar duplicados</content>
<parameter name="filePath">/home/lvalero/Proyectos/HiLuca/docker-deploy/webhooks/abyssale/README.md