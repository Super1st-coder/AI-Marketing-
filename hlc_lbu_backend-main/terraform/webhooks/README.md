# terraform/webhooks

Módulo Terraform para el **Webhook Gateway** de HiLuca.

Gestiona toda la infraestructura del servicio de webhooks reutilizable:

| Recurso | Nombre | Descripción |
|---------|--------|-------------|
| Service Account | `webhook-router-sa` | SA de la CF router |
| Cloud Function Gen2 | `webhook-router` | CF universal de entrada |
| API Gateway API | `hiluca-webhook-gateway` | API registrada |
| API Gateway Config | `webhook-gateway-config-v{N}` | OpenAPI spec compilado |
| API Gateway Gateway | `webhook-gateway` | Endpoint público |
| Secret Manager | `wh-secret-{servicio}` | Signing secret por proveedor |
| Pub/Sub Topic | `wh-{servicio}-{entorno}` | Cola de eventos por servicio+entorno |
| Pub/Sub DL Topic | `wh-{servicio}-dead-letter` | Cola de mensajes fallidos |
| Pub/Sub Subscription | `wh-sub-{servicio}-{entorno}` | Suscripción con dead-letter |
| GCS Bucket | `{project}-webhook-source` | Source code de las CFs |

---

## Prerrequisitos

1. El bucket de estado GCS debe existir:
   ```bash
   # Creado por terraform/infra/bootstrap — ya existe si usas el mismo proyecto
   gsutil ls gs://hiluca-lbu-tf-state
   ```

2. Las APIs del proyecto deben estar habilitadas (el módulo las habilita automáticamente).

---

## Workflow de deploy

### 1. Generar el ZIP de la CF webhook-router

```bash
# Desde la raíz del repo
cd webhooks/router
zip -r source.zip main.py verifiers.py registry.py requirements.txt

# Obtener el hash MD5 (necesario para terraform.tfvars)
md5 -q source.zip
```

### 2. Configurar variables

```bash
cd terraform/webhooks
cp terraform.tfvars.example terraform.tfvars
# Edita terraform.tfvars con:
#   - El hash MD5 del ZIP
#   - project_id, project_number
```

### 3. Init y apply

```bash
cd terraform/webhooks
terraform init
terraform plan
terraform apply
```

### 4. Subir el signing secret de AppFlyer

```bash
# Obtener el secret de AppFlyer del panel de AppsFlyer:
# Dashboard → Configuration → Integrated Partners → Postback → Signing Secret

echo -n "TU_SIGNING_SECRET_APPSFLYER" | \
  gcloud secrets versions add wh-secret-appsflyer \
    --data-file=- \
    --project=careful-acumen-422922-k4
```

### 5. Verificar el gateway

```bash
# Obtener la URL del gateway
terraform output webhook_gateway_url

# Probar health check
curl "https://<GATEWAY_URL>/webhook/health"

# Probar con AppFlyer en dev (sin firma)
curl -X POST "https://<GATEWAY_URL>/webhook/appsflyer/v1.0.0/dev" \
  -H "Content-Type: application/json" \
  -d '{"appsflyer_id": "test-001", "event_name": "install"}'
```

### 6. Configurar DNS

Después de que terraform output muestre el `webhook_gateway_url`:

```
integrate.hiluca.com  CNAME  <GATEWAY_URL>
```

---

## Actualizar el código de la CF

Cuando cambias `webhooks/router/*.py`:

```bash
# 1. Regenerar ZIP
cd webhooks/router
zip -r source.zip main.py verifiers.py registry.py requirements.txt

# 2. Obtener nuevo hash
HASH=$(md5 -q source.zip)

# 3. Actualizar terraform.tfvars
sed -i '' "s/webhook_router_source_hash.*/webhook_router_source_hash = \"$HASH\"/" \
  terraform/webhooks/terraform.tfvars

# 4. Apply
cd terraform/webhooks
terraform apply
```

## Actualizar el API Gateway (cambio al OpenAPI spec)

Cuando cambias `webhooks/gateway/api-config.yaml`:

```bash
# Incrementar gateway_config_version en terraform.tfvars
# v1 → v2 → v3 ...
# Terraform crea la nueva config y actualiza el gateway (zero-downtime)
terraform apply
```

## Agregar un nuevo servicio de webhook

```bash
# 1. Agregar el slug en terraform.tfvars:
#    webhook_services = ["appsflyer", "mi-nuevo-servicio"]

# 2. Apply (crea topics, secret, subscriptions automáticamente)
terraform apply

# 3. Subir el signing secret
echo -n "MI_SECRET" | gcloud secrets versions add wh-secret-mi-nuevo-servicio \
  --data-file=- --project=careful-acumen-422922-k4

# 4. Actualizar registry.py y redeploy del router (pasos 1-4 de "Actualizar CF")
```
