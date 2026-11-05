#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# startup.sh – Bootstrap de la VM de Compute Engine para HiLuca LBU
#
# Variables inyectadas por Terraform templatefile():
#   PROJECT_ID          = ${project_id}
#   ENVIRONMENT         = ${environment}
#   ENV_SECRET_NAME     = ${env_secret_name}
#   SQL_CONNECTION_NAME = ${sql_connection_name}
#   AR_PREFIX           = ${ar_prefix}
#   REGION              = ${region}
#   DB_ADMIN_USER       = ${db_admin_user}
#   DB_NAME_STRAPI      = ${db_name_strapi}
#   DB_NAME_SINERGIA    = ${db_name_sinergia}
#   DB_READER_PASSWORD  = ${db_reader_password}  (sensible)
#   DB_WRITER_PASSWORD  = ${db_writer_password}  (sensible)
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="${project_id}"
ENVIRONMENT="${environment}"
ENV_SECRET_NAME="${env_secret_name}"
SQL_CONNECTION_NAME="${sql_connection_name}"
AR_PREFIX="${ar_prefix}"
REGION="${region}"
DB_ADMIN_USER="${db_admin_user}"
DB_NAME_STRAPI="${db_name_strapi}"
DB_NAME_SINERGIA="${db_name_sinergia}"
DB_READER_PASSWORD="${db_reader_password}"
DB_WRITER_PASSWORD="${db_writer_password}"
APP_DIR="/app"

echo "==> [startup] HiLuca LBU – Bootstrap VM [$${ENVIRONMENT}]"
echo "    Proyecto: $PROJECT_ID | Región: $REGION"

# ── 1. Actualizar sistema ──────────────────────────────────────────────────────
echo "==> [1/8] Actualizando paquetes..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release git jq netcat-openbsd apt-transport-https

# ── 2. Instalar Docker Engine ──────────────────────────────────────────────────
echo "==> [2/8] Instalando Docker Engine..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get install -y -qq \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

usermod -aG docker debian
echo "==> [2/8] Docker instalado ✓"

# ── 3. Configurar Artifact Registry ───────────────────────────────────────────
echo "==> [3/8] Configurando Artifact Registry..."
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
sudo -u debian gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet || true

# ── 4. Crear directorios de la aplicación ────────────────────────────────────
echo "==> [4/8] Preparando directorio de la app..."
mkdir -p "$APP_DIR/nginx"

# Metadata del ambiente para uso por systemd y scripts
cat > "$APP_DIR/.env-meta" << EOF
ENVIRONMENT=$ENVIRONMENT
PROJECT_ID=$PROJECT_ID
CLOUD_SQL_CONNECTION_NAME=$SQL_CONNECTION_NAME
ENV_SECRET_NAME=$ENV_SECRET_NAME
AR_PREFIX=$AR_PREFIX
REGION=$REGION
EOF

# ── 5. Descargar .env desde Secret Manager ────────────────────────────────────
echo "==> [5/8] Descargando .env [$ENVIRONMENT] desde Secret Manager..."
if gcloud secrets versions access latest \
    --secret="$ENV_SECRET_NAME" \
    --project="$PROJECT_ID" \
    > "$APP_DIR/.env" 2>/dev/null; then
  echo "    .env descargado de Secret Manager [$ENV_SECRET_NAME] ✓"
  chmod 600 "$APP_DIR/.env"
else
  echo "    ADVERTENCIA: Secret [$ENV_SECRET_NAME] no encontrado."
  echo "    Crea la versión con:"
  echo "      gcloud secrets versions add $ENV_SECRET_NAME --data-file='.env.$ENVIRONMENT'"
  touch "$APP_DIR/.env"
fi

# Inyectar variables de infraestructura si no existen en el .env
grep -q "CLOUD_SQL_CONNECTION_NAME" "$APP_DIR/.env" || \
  echo "CLOUD_SQL_CONNECTION_NAME=$SQL_CONNECTION_NAME" >> "$APP_DIR/.env"
grep -q "AR_PREFIX" "$APP_DIR/.env" || \
  echo "AR_PREFIX=$AR_PREFIX" >> "$APP_DIR/.env"
grep -q "ENVIRONMENT" "$APP_DIR/.env" || \
  echo "ENVIRONMENT=$ENVIRONMENT" >> "$APP_DIR/.env"

# ── 6. Systemd service ────────────────────────────────────────────────────────
echo "==> [6/8] Configurando servicio systemd hiluca-lbu-$ENVIRONMENT..."
cat > "/etc/systemd/system/hiluca-lbu.service" << SYSTEMD_EOF
[Unit]
Description=HiLuca LBU [$ENVIRONMENT] – Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR

# Refrescar .env desde Secret Manager en cada arranque
ExecStartPre=/bin/bash -c ' \
  source $APP_DIR/.env-meta; \
  new_env=\$(gcloud secrets versions access latest \
    --secret="\$ENV_SECRET_NAME" --project="\$PROJECT_ID" 2>/dev/null); \
  if [ -n "\$new_env" ]; then \
    echo "\$new_env" > $APP_DIR/.env; \
    echo "CLOUD_SQL_CONNECTION_NAME=\$CLOUD_SQL_CONNECTION_NAME" >> $APP_DIR/.env; \
    echo "AR_PREFIX=\$AR_PREFIX" >> $APP_DIR/.env; \
    echo "ENVIRONMENT=\$ENVIRONMENT" >> $APP_DIR/.env; \
  fi \
'

ExecStart=/usr/bin/docker compose -f $APP_DIR/docker-compose.prod.yaml up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f $APP_DIR/docker-compose.prod.yaml down

TimeoutStartSec=300
TimeoutStopSec=120
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

systemctl daemon-reload
systemctl enable hiluca-lbu.service
echo "==> [6/8] Servicio systemd configurado ✓"

# ── 7. Provisioning de usuarios en Cloud SQL ─────────────────────────────────
echo "==> [7/8] Instalando Cloud SQL Proxy y provisionando usuarios DB..."

# Instalar cloud-sql-proxy si no está presente
if ! command -v cloud-sql-proxy &>/dev/null; then
  PROXY_VERSION="2.14.1"
  curl -fSsL \
    "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v$${PROXY_VERSION}/cloud-sql-proxy.linux.amd64" \
    -o /usr/local/bin/cloud-sql-proxy
  chmod +x /usr/local/bin/cloud-sql-proxy
  echo "    cloud-sql-proxy v$${PROXY_VERSION} instalado ✓"
fi

# Instalar psql (cliente PostgreSQL) si no está presente
if ! command -v psql &>/dev/null; then
  apt-get install -y -qq postgresql-client
fi

# Arrancar el proxy con socket unix en /cloudsql (background)
mkdir -p /cloudsql
cloud-sql-proxy \
  "$SQL_CONNECTION_NAME" \
  --unix-socket=/cloudsql \
  --quiet &
PROXY_PID=$!
echo "    Cloud SQL Proxy arrancado (PID: $PROXY_PID)"

# Obtener el script de provisioning desde la metadata de la instancia GCE
# (Terraform lo inyectó como 'init-db-users-script' en templatefile)
INIT_SCRIPT="/usr/local/bin/init_db_users.sh"
curl -fsSL \
  -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/init-db-users-script" \
  -o "$INIT_SCRIPT"
chmod +x "$INIT_SCRIPT"

bash "$INIT_SCRIPT" || echo "ADVERTENCIA: init_db_users.sh falló – revisar logs en /var/log/syslog"

# Detener el proxy temporal
kill "$PROXY_PID" 2>/dev/null || true
echo "==> [7/8] Usuarios DB provisionados ✓"

# ── 8. Permisos finales ────────────────────────────────────────────────────────
echo "==> [8/8] Ajustando permisos..."
chown -R debian:debian "$APP_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  VM Bootstrap completo – Ambiente: $ENVIRONMENT"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  App dir:    $APP_DIR"
echo "║  Cloud SQL:  $SQL_CONNECTION_NAME"
echo "║  AR Prefix:  $AR_PREFIX"
echo "║  DB Usuarios: strapi_reader/writer, sinergia_reader/writer"
echo "║"
echo "║  Próximos pasos (GitHub Actions lo hace automático):"
echo "║   1. Copia docker-compose.prod.yaml y nginx/ a $APP_DIR/"
echo "║   2. systemctl start hiluca-lbu"
echo "╚══════════════════════════════════════════════════════════════════╝"
