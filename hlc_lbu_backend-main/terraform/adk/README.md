# ADK Multi-Agent Service – Terraform

Despliega el servicio **Google Ads ADK** (`adk/google_ads_agents`) en **Cloud Run** con acceso **exclusivo por VPN**. Ningún cliente de internet puede alcanzar el servicio.

## Arquitectura de Seguridad

```
[Cliente en VPN]
      │
      │ DNS: adk.hiluca.internal → 10.8.0.1 (dnsmasq en servidor VPN)
      │
      ▼
[nginx en VPN server (dentro del VPC)]
      │
      │ Authorization: Bearer <GCP identity token>
      │ (compute SA del servidor VPN, refresco automático cada 45 min via cron)
      │
      ▼
[Cloud Run – ingress=INGRESS_TRAFFIC_INTERNAL_ONLY]
  hiluca-adk-dev-*.run.app  (port 8000)
           ADK Web UI 🤖
```

| Control de Seguridad | Implementación |
|---------------------|----------------|
| Aislamiento de red | `ingress=INTERNAL_ONLY` en Cloud Run – rechaza todo tráfico público |
| VPN enforcement | Solo IPs `10.8.0.0/24` (pool OpenVPN) enrutadas al VPC Connector |
| Auth del proxy | nginx agrega `Authorization: Bearer <token>` usando el compute SA del servidor VPN |
| IAM mínimo | SA dedicado con 4 roles + compute SA del VPN server con `roles/run.invoker` |
| Sin `allUsers` | Bloqueado por org policy – solo SAs/usuarios explícitos tienen `run.invoker` |
| Gestión de secretos | 10 secrets individuales en Secret Manager, nunca en la imagen |
| Egress controlado | Todo el egress pasa por el VPC Connector (auditable) |

---

## Pre-requisitos

1. La imagen Docker del ADK debe estar en Artifact Registry:
   ```bash
   # Desde el directorio raíz del proyecto
   cd adk/
   docker build -t us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev .
   docker push us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev
   ```

2. El OpenVPN server de `terraform/openvpn/` debe estar activo y conectado.

---

## Despliegue

### 1. Configurar variables

```bash
cd terraform/adk/
cp terraform.tfvars.example terraform.tfvars
# Edita terraform.tfvars con tus valores
```

### 2. Inicializar y aplicar

```bash
terraform init
terraform plan
terraform apply
```

### 3. Cargar los secretos en Secret Manager

Después del `terraform apply`, los secretos existen en Secret Manager pero **sin valor**. Carga los valores desde tu `.env` local:

```bash
# Lee los valores de tu .env y cárgalos (NO hardcodees en el repo)
echo -n "FALSE" | gcloud secrets versions add adk-google-genai-use-vertexai --data-file=-
echo -n "$(grep GOOGLE_API_KEY adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-api-key --data-file=-
echo -n "$(grep SERPAPI_KEY adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-serpapi-key --data-file=-
echo -n "$(grep NEWSAPI_KEY adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-newsapi-key --data-file=-
echo -n "$(grep ^GOOGLE_ADS_CUSTOMER_ID adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-customer-id --data-file=-
echo -n "$(grep GOOGLE_ADS_LOGIN_CUSTOMER_ID adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-login-customer-id --data-file=-
echo -n "$(grep GOOGLE_ADS_DEVELOPER_TOKEN adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-developer-token --data-file=-
echo -n "$(grep GOOGLE_ADS_CLIENT_ID adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-client-id --data-file=-
echo -n "$(grep GOOGLE_ADS_CLIENT_SECRET adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-client-secret --data-file=-
echo -n "$(grep GOOGLE_ADS_REFRESH_TOKEN adk/google_ads_agents/.env | cut -d= -f2)" | gcloud secrets versions add adk-google-ads-refresh-token --data-file=-
```

### 4. Otorgar acceso al compute SA del servidor VPN (una sola vez)

El servidor OpenVPN usa su propio **compute Service Account** para autenticar los requests de nginx hacia Cloud Run. Ejecuta esto una vez desde tu Mac (requiere estar autenticado con `gcloud`):

```bash
# Obtener el email del compute SA del servidor VPN
SA=$(gcloud compute instances describe vpn-network-vpn \
      --zone=us-central1-a \
      --project=careful-acumen-422922-k4 \
      --format='value(serviceAccounts[0].email)')

echo "VPN SA: $SA"   # Verifica que no esté vacío

# Otorgar run.invoker al compute SA
gcloud run services add-iam-policy-binding hiluca-adk-dev \
  --region=us-central1 \
  --project=careful-acumen-422922-k4 \
  --member="serviceAccount:$SA" \
  --role="roles/run.invoker"
```

### 5. Agregar usuarios individuales al servicio (opcional)

Si un usuario necesita invocar Cloud Run directamente (no sólo vía nginx):

```bash
gcloud run services add-iam-policy-binding hiluca-adk-dev \
  --region=us-central1 \
  --member="user:victor@hiluca.com" \
  --role="roles/run.invoker"

# O todo el equipo con un grupo:
# --member="group:equipo@hiluca.com"
```

### 6. Conectar la VPN y abrir el UI

```bash
# 1. Conéctate al OpenVPN (Tunnelblick, OpenVPN Connect, etc.)

# 2. Verifica que el DNS funciona (debe resolver a 10.8.0.1)
nslookup adk.hiluca.internal

# 3. Abre en el browser. Selecciona "google_ads_agents" en el dropdown.
open http://adk.hiluca.internal
```

> **¿Por qué `http://adk.hiluca.internal` y no la URL de `.run.app`?**
> Cloud Run con `ingress=INTERNAL_ONLY` rechaza cualquier request que no vengan del VPC interno,
> incluso estando en VPN. El nginx del servidor VPN actúa como reverse proxy: recibe tu request,
> agrega el Bearer token de autenticación, y lo reenvía a Cloud Run desde dentro del VPC.


---

## Variables

| Variable | Default | Descripción |
|----------|---------|-------------|
| `project_id` | — | ID del proyecto GCP |
| `region` | `us-central1` | Región para Cloud Run y VPC Connector |
| `environment` | — | `dev` o `prd` |
| `image_tag` | `dev` | Tag de la imagen Docker |
| `vpc_network` | `default` | VPC que tiene el peering con OpenVPN |
| `vpc_connector_subnet_cidr` | `10.8.1.0/28` | Subred /28 libre para el VPC Connector |
| `vpn_pool_cidr` | `10.8.0.0/24` | Pool de IPs del cliente OpenVPN |
| `cloud_run_min_instances` | `0` | 0 en dev, 1 en prd |
| `cloud_run_memory` | `1Gi` | RAM por instancia |

---

## Deploy & Update Workflow

### Caso A: Cambios en el código del agente (agent, tools, prompts, config)

```bash
# 1. Desde el directorio raíz del repo
cd adk/

# 2. Rebuild la imagen con los cambios
docker build -t us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev .

# 3. Push al Artifact Registry
docker push us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev

# 4. Forzar un nuevo revision en Cloud Run con la nueva imagen
#    ⚠️ Usar `gcloud run deploy`, NO `gcloud run services update` (este último
#    requiere un cambio de configuración explícito y no re-pull del mismo tag).
gcloud run deploy hiluca-adk-dev \
  --image us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev \
  --region us-central1 \
  --project careful-acumen-422922-k4
```

> **¿Por qué `gcloud run deploy` y no `gcloud run services update`?**
> Cloud Run identifica revisiones por imagen digest, no por tag. Si el tag `dev` apunta
> a un nuevo digest (mismo tag, nueva imagen), `services update` sin flags dice
> _"No configuration change requested"_. `gcloud run deploy --image` fuerza el pull
> del digest actual del tag y crea una nueva revisión.

---

### Caso B: Cambios en infraestructura (IAM, secretos, env vars, memoria, etc.)

```bash
cd terraform/adk/

terraform plan   # Revisa el plan antes de aplicar
terraform apply
```

Después del `apply`, Cloud Run crea automáticamente una nueva revisión con la nueva config.
**No necesitas hacer `docker build` si solo cambias infra.**

---

### Caso C: Ambos (código + infra)

```bash
# 1. Build y push la imagen
cd adk/
docker build -t us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev .
docker push us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev

# 2. Terraform aplica los cambios de infra Y despliega la nueva imagen en un solo paso
cd ../terraform/adk/
terraform apply
```

---

### Rotar un secreto de Google Ads

```bash
# Agrega una nueva versión del secreto (Cloud Run resuelve "latest" automáticamente)
echo -n "NUEVO_VALOR" | gcloud secrets versions add adk-google-ads-refresh-token --data-file=-

# Fuerza una nueva revisión para que tome el nuevo valor
gcloud run deploy hiluca-adk-dev \
  --image us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository/adk:dev \
  --region us-central1 \
  --project careful-acumen-422922-k4
```

---

### Verificar que el deploy está activo (en VPN)

```bash
# DNS debe resolver a 10.8.0.1 (nginx en VPN server)
nslookup adk.hiluca.internal

# HTTP debe devolver 200 con el HTML del ADK Web UI
curl -i http://adk.hiluca.internal/

# O abrir en el browser
open http://adk.hiluca.internal
```

> **Cold start:** Si `cloud_run_min_instances = 0` (dev), el primer request después de
> inactividad tarda ~30–60s. El startup probe permite hasta 3 minutos antes de marcar
> la revisión como fallida.
