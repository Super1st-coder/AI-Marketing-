# HiLuca LBU – Infraestructura GCP

Módulo Terraform que provisiona el stack completo de **HiLuca LBU** en Google Cloud Platform.

## Arquitectura

```
Internet
   │  :80 (redirect)  :443 (HTTPS)
   ▼
┌─────────────────────────────────┐
│   Cloud Load Balancer (Global)  │  ← IP estática + Google-managed SSL cert
│   + Cloud Armor WAF             │    (SQLi, XSS, LFI, RFI)
└────────────────┬────────────────┘
                 │ HTTP :80
                 ▼
┌─────────────────────────────────┐
│   Compute Engine (Debian 12)    │  e2-standard-2 en prd
│                                 │
│  ┌──────────────────────────┐   │
│  │  nginx (reverse proxy)   │   │
│  │  :80 → strapi/n8n/sinerg │   │
│  ├──────────────────────────┤   │
│  │  strapi       :1337      │   │
│  │  n8n          :5678      │   │
│  │  sinergia     :60000     │   │
│  │  redis        :6379      │   │
│  │  mongodb      :27017     │   │
│  │  cloud-sql-proxy :5432   │   │
│  └──────────────────────────┘   │
└────────────────┬────────────────┘
                 │ Cloud SQL Auth Proxy
                 ▼
┌─────────────────────────────────┐
│   Cloud SQL – PostgreSQL 15     │  Backups diarios, PITR
│   DBs: strapi | sinergia        │
└─────────────────────────────────┘

Apoyo:
  Secret Manager  → .env por ambiente
  Artifact Registry → imágenes Docker (strapi, sinergia)
  GCS Bucket      → terraform.tfstate por workspace
  Cloud Monitoring → uptime check + alertas email
```

## Ambientes

| Recurso | dev | qas | prd |
|---|---|---|---|
| VM | `e2-micro` | `e2-standard-2` | `e2-standard-2` |
| Disco VM | 20 GB | 30 GB | 50 GB |
| Cloud SQL | `db-f1-micro` | `db-g1-small` | `db-g1-small` |
| Backups SQL | ❌ | ✅ | ✅ |
| Deletion protection | ❌ | ❌ | ✅ |
| Cloud Armor WAF | ❌ | ✅ | ✅ |
| Uptime + alertas | ❌ | ✅ | ✅ |
| Dominio | `dev.hiluca.com` | `qas.hiluca.com` | `sec.hiluca.com` |

## Pre-requisitos

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) autenticado: `gcloud auth application-default login`
- Proyecto GCP: `careful-acumen-422922-k4` con billing habilitado
- Par de llaves SSH para GitHub Actions (una por ambiente)

## Primera vez (setup inicial)

### 1. Crear el bucket de Terraform state

```bash
bash bootstrap/create-state-bucket.sh
```

Esto crea `gs://hiluca-lbu-tf-state` con versionado habilitado. **Solo se ejecuta una vez.**

### 2. Generar llaves SSH para GitHub Actions

```bash
# Una por ambiente
ssh-keygen -t ed25519 -C "github-actions-dev@hiluca"  -f ~/.ssh/gh_actions_hiluca_dev
ssh-keygen -t ed25519 -C "github-actions-qas@hiluca"  -f ~/.ssh/gh_actions_hiluca_qas
ssh-keygen -t ed25519 -C "github-actions-prd@hiluca"  -f ~/.ssh/gh_actions_hiluca_prd
```

Guarda las llaves **privadas** en GitHub Secrets:
- `VM_SSH_KEY_DEV` → contenido de `~/.ssh/gh_actions_hiluca_dev`
- `VM_SSH_KEY_QAS` → contenido de `~/.ssh/gh_actions_hiluca_qas`
- `VM_SSH_KEY_PRD` → contenido de `~/.ssh/gh_actions_hiluca_prd`

Copia el contenido de los `.pub` correspondientes en cada `env/*.tfvars`.

### 3. Configurar las variables por ambiente

```bash
# Copia el ejemplo y edita
cp terraform.tfvars.example env/dev.tfvars   # ya existe, solo editar
```

Campos obligatorios en cada `env/*.tfvars`:

| Variable | Descripción |
|---|---|
| `gh_actions_ssh_public_key` | Contenido del archivo `.pub` |
| `db_password` | Contraseña segura de Cloud SQL |
| `alert_email` | Email para alertas (qas y prd) |

### 4. Subir el .env a Secret Manager

El Secret Manager **solo crea el secret** con Terraform (sin contenido).
El contenido se sube manualmente o desde CI/CD:

```bash
# Cada ambiente tiene su propio secret
gcloud secrets versions add hiluca-lbu-dev-env \
  --data-file=".env.dev" --project=careful-acumen-422922-k4

gcloud secrets versions add hiluca-lbu-qas-env \
  --data-file=".env.qas" --project=careful-acumen-422922-k4

gcloud secrets versions add hiluca-lbu-prd-env \
  --data-file=".env.prd" --project=careful-acumen-422922-k4
```

El `.env` de producción debe incluir además de las variables del `.env` original:

```env
CLOUD_SQL_CONNECTION_NAME=careful-acumen-422922-k4:us-central1:hiluca-lbu-prd-postgres
AR_PREFIX=us-central1-docker.pkg.dev/careful-acumen-422922-k4/hiluca-docker-repository
DATABASE_HOST=cloud-sql-proxy
DATABASE_PORT=5432
ENVIRONMENT=prd
```

## Flujo de deploy por ambiente

```bash
cd terraform/infra

# ── Dev ──────────────────────────────────────────────────────
terraform workspace new dev          # solo la primera vez
terraform workspace select dev
terraform init
terraform plan  -var-file=env/dev.tfvars
terraform apply -var-file=env/dev.tfvars

# ── QAS ──────────────────────────────────────────────────────
terraform workspace new qas          # solo la primera vez
terraform workspace select qas
terraform init
terraform plan  -var-file=env/qas.tfvars
terraform apply -var-file=env/qas.tfvars

# ── PRD ──────────────────────────────────────────────────────
terraform workspace new prd          # solo la primera vez
terraform workspace select prd
terraform init
terraform plan  -var-file=env/prd.tfvars
terraform apply -var-file=env/prd.tfvars
```

## Post-deploy

Tras el primer `terraform apply`, Terraform imprime los `outputs` con los pasos exactos.
Los puntos manuales son:

1. **DNS**: Apunta el dominio del ambiente a `load_balancer_ip` del output
   ```
   dev.hiluca.com  → A  <lb_ip>
   qas.hiluca.com  → A  <lb_ip>
   sec.hiluca.com  → A  <lb_ip>
   ```
   El certificado SSL tarda ~15 min en provisionarse tras propagar el DNS.

2. **Primer deploy de la app**: GitHub Actions hace SSH a `vm_external_ip` y corre:
   ```bash
   docker compose -f /app/docker-compose.prod.yaml pull
   docker compose -f /app/docker-compose.prod.yaml up -d
   ```

## Estructura de archivos

```
terraform/infra/
├── backend.tf              # GCS remote state + provider
├── main.tf                 # Compute Engine, Cloud SQL, Load Balancer
├── cloud_armor.tf          # WAF: SQLi, XSS, LFI, RFI
├── monitoring.tf           # Uptime check + alertas email
├── variables.tf            # Definición de todas las variables
├── outputs.tf              # IPs, connection names, instrucciones post-deploy
├── terraform.tfvars        # No contiene valores (ver env/)
├── terraform.tfvars.example
├── env/
│   ├── dev.tfvars          # ← editado con tus valores reales
│   ├── qas.tfvars          # ← editado con tus valores reales
│   └── prd.tfvars          # ← editado con tus valores reales (¡no commitear!)
├── scripts/
│   └── startup.sh          # Bootstrap de la VM al crear/reiniciar
└── bootstrap/
    └── create-state-bucket.sh
```

## Archivos en la raíz del repo

| Archivo | Propósito |
|---|---|
| `docker-compose.prod.yaml` | Stack de producción (sin strapiDB, con Cloud SQL Auth Proxy y nginx) |
| `nginx/nginx.conf` | Reverse proxy: `/n8n/` → n8n, `/sinergia/` → sinergia, `/` → strapi |

## Destruir un ambiente

```bash
# ⚠️  prd tiene deletion_protection=true en Cloud SQL.
# Primero cambia a false y aplica, luego destruye.
terraform workspace select dev
terraform destroy -var-file=env/dev.tfvars
```

## Troubleshooting

| Síntoma | Causa probable |
|---|---|
| LB responde 502 | Docker Compose no está corriendo en la VM. SSH y revisar `docker compose ps` |
| Certificado SSL pendiente | DNS aún no propagado. Verifica con `dig sec.hiluca.com` |
| `cloud-sql-proxy` no conecta | El SA de la VM no tiene `roles/cloudsql.client`. Verifica IAM. |
| Strapi no arranca | Cloud SQL Auth Proxy no está healthy. Revisar `docker logs hiluca-cloud-sql-proxy` |
| `terraform init` falla | El bucket `hiluca-lbu-tf-state` no existe. Corre el bootstrap script. |
