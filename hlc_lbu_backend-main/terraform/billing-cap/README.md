# Billing Cap – Cloud Function

Protección automática contra sobrecostos en GCP. Cuando el gasto acumulado del mes supera el límite configurado (en MXN), una Cloud Function deshabilita el billing de los proyectos protegidos, deteniendo el cobro sin eliminar los recursos.

## Arquitectura

```
GCP Billing Budget
 (30,000 MXN / 4 umbrales)
         │
         ├── Email alerts (50%, 80%, 100%, 110%) → administradores de facturación
         │
         └── Pub/Sub: billing-budget-alerts  ← TIEMPO REAL
                  │
                  └── billing-cap-pubsub (Cloud Function Gen 2)
                           │  entry point: stop_billing
                           └── Cloud Billing API → deshabilita billing

Cloud Scheduler (*/5 min)  ← REDUNDANCIA / FALLBACK
         │
         │  HTTP POST + OIDC token
         ▼
  billing-cap (Cloud Function Gen 2)
         │
         │  Cloud Monitoring API
         │  billing/monthly_cost → gasto real del mes
         │
         ├── Gasto < 30,000 MXN → sin acción, log informativo
         │
         └── Gasto >= 30,000 MXN → Cloud Billing API
                  │
                  ├── Modo 1: Lista explícita de proyectos
                  │
                  └── Modo 2: Todos los proyectos de la billing account
                              EXCEPTO los excluidos
                  │
                  ▼
         updateBillingInfo → billing_account_name: ""
```

**Dos capas de protección:**
- **Budget → Pub/Sub → `billing-cap-pubsub`**: reacción en tiempo real cuando GCP detecta que se cruzó un umbral.
- **Cloud Scheduler → `billing-cap`**: polling cada 5 minutos vía Cloud Monitoring. Actúa como redundancia si el mensaje Pub/Sub no llega o falla.

### Componentes desplegados

| Recurso | Nombre | Descripción |
|---|---|---|
| Service Account | `billing-cap-sa` | Identidad de ambas Cloud Functions |
| Service Account | `billing-cap-scheduler` | SA del Cloud Scheduler (invoker HTTP) |
| Pub/Sub Topic | `billing-budget-alerts` | Recibe alertas del Budget → dispara `billing-cap-pubsub` |
| Billing Budget | `Monthly Cap - 30000 MXN` | Monitorea el gasto con 4 umbrales + conectado al topic |
| GCS Bucket | `{project}-billing-cap-src` | Almacena el ZIP del código fuente |
| Cloud Function Gen 2 | `billing-cap` | Polling vía Cloud Monitoring, invocada por Scheduler (HTTP) |
| Cloud Function Gen 2 | `billing-cap-pubsub` | Trigger Pub/Sub tiempo real, entry point `stop_billing` |
| Cloud Scheduler | `billing-cap-check` | Invoca `billing-cap` cada 5 minutos con OIDC |

### Umbrales del budget

| Threshold | Base | Acción |
|---|---|---|
| 50% ($15,000 MXN) | Gasto real | Email informativo |
| 80% ($24,000 MXN) | Gasto real | Email de advertencia |
| **100% ($30,000 MXN)** | **Gasto real** | **Email + Pub/Sub → `billing-cap-pubsub` desactiva billing (tiempo real)** |
| **110% ($33,000 MXN)** | **Pronóstico** | **Email de alerta de pronóstico** |

> **Latencia de reacción:**
> - **Pub/Sub**: GCP dispara el mensaje en minutos desde que se cruza el umbral → `billing-cap-pubsub` actúa de inmediato.
> - **Cloud Scheduler**: polling cada 5 minutos via Cloud Monitoring → latencia máxima ~5 min (redundancia).

---

## Workaround DRS (Domain Restricted Sharing)

La organización tiene la org policy `constraints/iam.allowedPolicyMemberDomains` activa, que impide agregar
service accounts externas al dominio en IAM. Esto normalmente bloquea la conexión Budget → Pub/Sub
porque la Budget API necesita otorgar `roles/pubsub.publisher` a su service agent interno.

### Solución aplicada durante el deploy inicial

Se creó temporalmente un override a nivel de proyecto que neutralizaba la DRS solo para
`careful-acumen-422922-k4`, permitiendo que `terraform apply` conectara el Budget al topic:

```bash
# 1. Crear override (neutraliza DRS para este proyecto)
gcloud org-policies reset constraints/iam.allowedPolicyMemberDomains \
  --project=careful-acumen-422922-k4

# 2. Aplicar Terraform (conecta Budget → Pub/Sub)
terraform apply

# 3. Eliminar el override (restaura DRS de la org)
#    El IAM binding del Budget→Pub/Sub YA QUEDÓ guardado — persiste aunque se restaure la DRS.
gcloud org-policies delete constraints/iam.allowedPolicyMemberDomains \
  --project=careful-acumen-422922-k4
```

> **¿Por qué es seguro?**
> - El override duró solo durante el `terraform apply` (~segundos).
> - Una vez eliminado, la DRS de la org vuelve a aplicar.
> - El IAM binding interno del Budget API sobre el topic persiste — no se rompe al re-habilitar DRS.
> - El proyecto `careful-acumen-422922-k4` no contiene datos sensibles (solo Cloud Functions + Scheduler + topic).

### Si necesitas re-deployar desde cero

Repite los 3 pasos anteriores. El `lifecycle { ignore_changes = [] }` en el budget está vacío
intencionalmen te para que Terraform gestione `all_updates_rule` normalmente.


## Modos de protección

La función soporta dos modos controlados por variables de Terraform.

### Modo 1 – Lista explícita

Protege únicamente los proyectos que especifiques:

```hcl
protected_project_ids = ["mi-proyecto-dev", "mi-proyecto-staging"]
excluded_project_ids  = []
```

**Cuándo usarlo:** Tienes proyectos muy específicos que quieres monitorear y el resto no importa.

### Modo 2 – Todos excepto excluidos

Protege **todos** los proyectos de la billing account, saltando los que estén en la lista de excepciones:

```hcl
protected_project_ids = []
excluded_project_ids  = ["mi-proyecto-produccion", "mi-proyecto-ci-cd"]
```

**Cuándo usarlo:** Cuando quieres protección amplia sobre muchos proyectos, exentando solo los críticos.

> **Nota:** Si `protected_project_ids` tiene valores, siempre tiene prioridad sobre el Modo 2.

---

## Estructura de archivos

```
billing_cap/                      ← Código de la Cloud Function
├── main.py                       ← Lógica principal (entry point: check_billing_scheduler)
└── requirements.txt              ← Dependencias Python

terraform/billing-cap/            ← Infraestructura como código
├── main.tf                       ← Todos los recursos GCP
├── variables.tf                  ← Variables con validación
├── outputs.tf                    ← Outputs post-deploy
├── terraform.tfvars              ← Configuración local (en .gitignore)
└── README.md                     ← Este archivo
```

---

## Prerrequisitos

### Herramientas

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5.0
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) autenticado
- Python >= 3.11 (solo para pruebas locales)

### Permisos requeridos

Quien ejecute `terraform apply` necesita:

| Scope | Rol requerido |
|---|---|
| Proyecto host | `roles/owner` o `roles/editor` + APIs |
| Billing Account | `roles/billing.admin` |

La SA `billing-cap-sa` necesita `roles/billing.admin` en la billing account — **este permiso debe otorgarse manualmente** desde GCP Console o con `gcloud billing accounts add-iam-policy-binding`, ya que Terraform no puede gestionar IAM de billing accounts con ADC estándar.

```bash
gcloud billing accounts add-iam-policy-binding BILLING_ACCOUNT_ID \
  --member="serviceAccount:billing-cap-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/billing.admin"
```

### APIs habilitadas automáticamente por Terraform

- `cloudfunctions.googleapis.com`
- `cloudbuild.googleapis.com`
- `run.googleapis.com`
- `pubsub.googleapis.com`
- `billingbudgets.googleapis.com`
- `cloudbilling.googleapis.com`
- `eventarc.googleapis.com`
- `artifactregistry.googleapis.com`
- `cloudscheduler.googleapis.com`
- `monitoring.googleapis.com`

---

## Deploy

### 1. Configurar variables

```bash
cd terraform/billing-cap
# Crear terraform.tfvars (está en .gitignore)
```

Contenido mínimo de `terraform.tfvars`:

```hcl
host_project_id    = "mi-proyecto-gcp"
billing_account_id = "XXXXXX-XXXXXX-XXXXXX"
region             = "us-central1"

# Monto en MXN (la billing account usa pesos mexicanos)
# Referencia: ~$1,500 USD ≈ $30,000 MXN
budget_amount_mxn = 30000

# Modo 2: todos los proyectos excepto producción
protected_project_ids = []
excluded_project_ids  = []

# Fecha desde la que actúa la función (evita falsos positivos al hacer el primer deploy)
active_from = "2026-04-01"
```

> Tu `billing_account_id` lo encuentras en:
> GCP Console → Billing → Manage billing accounts → columna "ID"

### 2. Autenticar gcloud

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <host_project_id>
gcloud config set project <host_project_id>
```

### 3. Inicializar Terraform

```bash
terraform init
```

### 4. Revisar el plan

```bash
terraform plan
```

### 5. Aplicar

```bash
terraform apply
```

Confirma con `yes`. El deploy tarda ~2-3 minutos.

### 6. Otorgar billing.admin a la SA (paso manual)

```bash
gcloud billing accounts add-iam-policy-binding <BILLING_ACCOUNT_ID> \
  --member="serviceAccount:billing-cap-sa@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/billing.admin"
```

### 7. Verificar el deploy

```bash
# Ver outputs
terraform output

# Verificar que ambas funciones existen
gcloud functions list --gen2 --regions=us-central1

# Ver logs de la función HTTP (Scheduler)
gcloud functions logs read billing-cap --gen2 --region=us-central1

# Ver logs de la función Pub/Sub (Budget alerts)
gcloud functions logs read billing-cap-pubsub --gen2 --region=us-central1

# Ver el Cloud Scheduler job
gcloud scheduler jobs list --location=us-central1
```

---

## Prueba manual

### 1. Probar el trigger Pub/Sub (tiempo real)

Publica un mensaje simulado de Budget Alert directamente al topic. Usa un `alertThresholdExceeded` de `0.5` (50%) para probar sin que la función desactive el billing:

```bash
# Mensaje simulado de Budget Alert al 50% (no dispara desactivación)
gcloud pubsub topics publish billing-budget-alerts \
  --project=careful-acumen-422922-k4 \
  --message='{
    "budgetDisplayName": "Monthly Cap - 30000 MXN",
    "alertThresholdExceeded": 0.5,
    "costAmount": 15000.0,
    "budgetAmount": 30000.0,
    "costIntervalStart": "2026-04-01T00:00:00Z",
    "currencyCode": "MXN"
  }'
```

Verifica que `billing-cap-pubsub` recibió y procesó el mensaje:

```bash
gcloud functions logs read billing-cap-pubsub \
  --gen2 --region=us-central1 --limit=20
```

Deberías ver algo como:
```
Budget Alert | 'Monthly Cap - 30000 MXN' | Costo: 15000.00 | Límite: 30000.00 | Threshold: 50%
Threshold 50% < 100%. Sin acción.
```

> ⚠️ **Para probar la desactivación real** cambia `alertThresholdExceeded` a `1.0` — pero solo en un proyecto de prueba, ya que **realmente deshabilita el billing**.

---

### 2. Probar el Cloud Scheduler (redundancia)

```bash
gcloud scheduler jobs run billing-cap-check --location=us-central1
```

Revisa los logs:

```bash
gcloud functions logs read billing-cap --gen2 --region=us-central1 --limit=20
```

Deberías ver el gasto actual y si está por debajo del límite: `OK: XX.X% del presupuesto usado. Sin acción.`

---

### 3. Llamar la función HTTP directamente

```bash
curl -X POST https://billing-cap-bvuoyah6iq-uc.a.run.app \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json"
```

---


## Restaurar billing

Si el billing fue deshabilitado y quieres reactivarlo:

```bash
# Re-vincular la billing account al proyecto
gcloud billing projects link <PROJECT_ID> \
  --billing-account=<BILLING_ACCOUNT_ID>
```

O desde GCP Console: **Billing → Manage billing accounts → My projects → Link**.

---

## Destruir la infraestructura

```bash
terraform destroy
```

> El bucket de código se destruye con `force_destroy = true`. El budget y el Scheduler job se eliminarán, pero los proyectos ya desactivados **no** recuperan billing automáticamente — hay que re-vincularlos manualmente.

---

## Variables de referencia

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `host_project_id` | `string` | — | Proyecto donde vive la función |
| `billing_account_id` | `string` | — | ID de la billing account |
| `region` | `string` | `us-central1` | Región del deploy |
| `budget_amount_mxn` | `number` | `30000` | Límite mensual en **MXN** |
| `protected_project_ids` | `list(string)` | `[]` | Modo 1: proyectos a proteger |
| `excluded_project_ids` | `list(string)` | `[]` | Modo 2: proyectos exentos |
| `notification_channel_ids` | `list(string)` | `[]` | Canales Monitoring (email/Slack) |
| `active_from` | `string` | `""` | Fecha ISO desde la que actúa (YYYY-MM-DD) |
| `log_level` | `string` | `INFO` | Nivel de logging |
