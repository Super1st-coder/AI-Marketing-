# webhook-router

Cloud Function Gen2 universal para recibir webhooks de cualquier proveedor.

## Estructura de URL

```
https://integrate.hiluca.com/webhook/{servicio}/{version}/{entorno}
https://integrate.hiluca.com/webhook/{servicio}/{version}       ← default prd
```

| Segmento   |        Ejemplo        | Notas                                                 |
|------------|-----------------------|-------------------------------------------------------|
| `servicio` |     `appsflyer`       | Slug del proveedor, debe existir en `registry.py`     |
| `version`  |      `v1.0.0`         | Versión del contrato del webhook                      |
| `entorno`  | `dev` / `qas` / `prd` | Opcional — default: `prd`. En `dev` se omite la firma |

---

## Agregar un nuevo servicio

1. **Agregar al registry** (`registry.py`):
   ```python
   "mi-servicio": {
       "v1.0.0": {
           "verifier": "hmac_sha256",
           "secret_name": "wh-secret-mi-servicio",
           "signature_header": "x-my-signature",
           "idempotency_field": "event_id",
           "topic_pattern": "wh-mi-servicio-{entorno}",
       }
   }
   ```

2. **Crear el secret** en Secret Manager:
   ```bash
   echo -n "mi_signing_secret" | \
     gcloud secrets create wh-secret-mi-servicio \
       --data-file=- \
       --project=careful-acumen-422922-k4
   ```

3. **Crear los Pub/Sub topics**:
   ```bash
   gcloud pubsub topics create wh-mi-servicio-dev  --project=careful-acumen-422922-k4
   gcloud pubsub topics create wh-mi-servicio-prd  --project=careful-acumen-422922-k4
   ```

4. **Crear la CF procesadora** en `webhooks/mi-servicio/processor/main.py`

5. **Redeploy del router** (ver sección Deploy abajo)

---

## Deploy

### Variables de entorno requeridas
```
GOOGLE_CLOUD_PROJECT=careful-acumen-422922-k4
```

### Deploy de la CF webhook-router
```bash
PROJECT_ID="careful-acumen-422922-k4"
REGION="us-central1"

gcloud functions deploy webhook-router \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --trigger-http \
  --no-allow-unauthenticated \
  --source=. \
  --entry-point=webhook_router \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --service-account=401654669410-compute@developer.gserviceaccount.com \
  --project=$PROJECT_ID
```

### Obtener la URL de la CF (para el api-config.yaml)
```bash
gcloud functions describe webhook-router \
  --gen2 --region=us-central1 \
  --format='value(serviceConfig.uri)' \
  --project=careful-acumen-422922-k4
```
Reemplaza `<ROUTER_CF_URL>` en `gateway/api-config.yaml` con esta URL.

### Permisos IAM requeridos para la CF
```bash
PROJECT_ID="careful-acumen-422922-k4"
SA="401654669410-compute@developer.gserviceaccount.com"

# Publicar en Pub/Sub
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/pubsub.publisher"

# Leer secrets de Secret Manager
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"
```

### Deploy del API Gateway unificado
```bash
PROJECT_ID="careful-acumen-422922-k4"
REGION="us-central1"
API_ID="hiluca-webhook-gateway"
CONFIG_ID="webhook-gateway-config-v1"
GW_ID="webhook-gateway"

# Crear la API (solo la primera vez)
gcloud api-gateway apis create $API_ID --project=$PROJECT_ID

# Crear nueva config (reemplaza <ROUTER_CF_URL> en api-config.yaml primero)
gcloud api-gateway api-configs create $CONFIG_ID \
  --api=$API_ID \
  --openapi-spec=../gateway/api-config.yaml \
  --project=$PROJECT_ID

# Crear o actualizar el gateway
gcloud api-gateway gateways create $GW_ID \
  --api=$API_ID \
  --api-config=$CONFIG_ID \
  --location=$REGION \
  --project=$PROJECT_ID

# ── Actualizaciones subsecuentes:
# Incrementa el número de CONFIG_ID (v1 → v2, etc.) y usa:
gcloud api-gateway gateways update $GW_ID \
  --api=$API_ID \
  --api-config=$CONFIG_ID \
  --location=$REGION \
  --project=$PROJECT_ID
```

---

## Pruebas locales

```bash
# Instalar dependencias
pip install -r requirements.txt

# Correr la CF localmente
functions-framework --target=webhook_router --debug

# En otra terminal — simular webhook AppsFlyer (dev, sin firma)
curl -X POST "http://localhost:8080/webhook/appsflyer/v1.0.0/dev" \
  -H "Content-Type: application/json" \
  -d '{"appsflyer_id": "test-123", "event_name": "install", "app_id": "com.test.app"}'

# Simular webhook AppsFlyer (prd, con firma HMAC)
SECRET="mi_signing_secret"
PAYLOAD='{"appsflyer_id":"test-456","event_name":"PAYMENT_SUCCESS"}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
curl -X POST "http://localhost:8080/webhook/appsflyer/v1.0.0/prd" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$PAYLOAD"
```

---

## Compatibilidad con el simulador existente

El simulador de AppsFlyer en `webhooks/appflyer/simulator/` puede seguir usándose,
solo actualiza la URL:

```bash
# Antes (URL vieja)
python simulator/simulate_appsflyer_postbacks.py \
  --url "https://integrate.hiluca.com/" \
  ...

# Ahora (nueva estructura)
python simulator/simulate_appsflyer_postbacks.py \
  --url "https://integrate.hiluca.com/webhook/appsflyer/v1.0.0/dev" \
  ...
```

---

## Flujo de vida de un webhook

```
1.  Proveedor → POST /webhook/appsflyer/v1.0.0/prd
2.  API Gateway valida JWT → CF webhook-router
3.  Router parsea path → servicio=appsflyer, version=v1.0.0, entorno=prd
4.  Lookup SERVICE_REGISTRY → obtiene config
5.  Carga secret "wh-secret-appsflyer" desde Secret Manager
6.  Valida firma HMAC-SHA256 con header "x-signature"
      → ❌ Firma inválida → 401
      → ✅ Firma válida → continúa
7.  Genera idempotency_key = "appsflyer:v1.0.0:prd:<appsflyer_id>"
8.  Publica en Pub/Sub "wh-appsflyer-prd" con atributos
9.  Retorna 200 {"status": "ok", "message_id": "..."}
10. [Async] CF wh-proc-appsflyer consume → BigQuery
```
