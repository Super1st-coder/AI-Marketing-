#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# init_db_users.sh – Provisioning de usuarios y roles en PostgreSQL
#
# Ejecutado por startup.sh una sola vez, vía Cloud SQL Proxy (socket unix).
# Crea en cada DB:
#   • Rol  hiluca_readonly  → SELECT en todas las tablas
#   • Rol  hiluca_readwrite → SELECT, INSERT, UPDATE, DELETE en todas las tablas
#   • Usuario <DB>_reader   con contraseña, miembro de hiluca_readonly
#   • Usuario <DB>_writer   con contraseña, miembro de hiluca_readwrite
#
# Variables requeridas (inyectadas por templatefile desde main.tf):
#   DB_ADMIN_USER       = ${db_admin_user}
#   DB_NAME_STRAPI      = ${db_name_strapi}
#   DB_NAME_SINERGIA    = ${db_name_sinergia}
#   DB_READER_PASSWORD  = ${db_reader_password}
#   DB_WRITER_PASSWORD  = ${db_writer_password}
#   PROXY_SOCKET_DIR    = /cloudsql   (fijo – directorio del socket unix)
#   SQL_CONNECTION_NAME = ${sql_connection_name}
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

DB_ADMIN_USER="${db_admin_user}"
DB_NAME_STRAPI="${db_name_strapi}"
DB_NAME_SINERGIA="${db_name_sinergia}"
DB_READER_PASSWORD="${db_reader_password}"
DB_WRITER_PASSWORD="${db_writer_password}"
SQL_CONNECTION_NAME="${sql_connection_name}"
PROXY_SOCKET="/cloudsql/$SQL_CONNECTION_NAME"
SENTINEL="/var/lib/hiluca/.db_users_init_done"

# ── Idempotencia: no ejecutar si ya se inicializó ────────────────────────────
if [ -f "$SENTINEL" ]; then
  echo "==> [init_db_users] Ya ejecutado anteriormente. Saltando."
  exit 0
fi

echo "==> [init_db_users] Iniciando provisioning de usuarios DB..."

# ── Esperar al socket del Cloud SQL Proxy ────────────────────────────────────
echo "    Esperando socket Cloud SQL Proxy: $PROXY_SOCKET"
for i in $(seq 1 30); do
  if [ -S "$PROXY_SOCKET/.s.PGSQL.5432" ]; then
    echo "    Socket disponible ✓"
    break
  fi
  echo "    Intento $i/30 – esperando 5s..."
  sleep 5
done

if [ ! -S "$PROXY_SOCKET/.s.PGSQL.5432" ]; then
  echo "ERROR: El socket del Cloud SQL Proxy no está disponible después de 150s."
  echo "       Verifica que cloud-sql-proxy esté corriendo con --unix-socket /cloudsql"
  exit 1
fi

# ── Función helper: ejecutar SQL en una base de datos ────────────────────────
run_sql() {
  local db="$1"
  local sql="$2"
  PGPASSWORD="" psql \
    --host="$PROXY_SOCKET" \
    --username="$DB_ADMIN_USER" \
    --dbname="$db" \
    --no-password \
    -c "$sql"
}

# ── Función: provisionar una base de datos ───────────────────────────────────
provision_database() {
  local db_name="$1"
  local reader_user="$${db_name}_reader"
  local writer_user="$${db_name}_writer"

  echo ""
  echo "  ── Provisionando base de datos: $db_name ──────────────────────────"

  # 1. Crear roles si no existen
  run_sql "postgres" "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hiluca_readonly') THEN
    CREATE ROLE hiluca_readonly NOLOGIN;
    RAISE NOTICE 'Rol hiluca_readonly creado';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hiluca_readwrite') THEN
    CREATE ROLE hiluca_readwrite NOLOGIN;
    RAISE NOTICE 'Rol hiluca_readwrite creado';
  END IF;
END
\$\$;"

  # 2. Crear usuario reader si no existe y asignar contraseña
  run_sql "postgres" "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$reader_user') THEN
    CREATE USER $reader_user WITH LOGIN PASSWORD '$DB_READER_PASSWORD';
    RAISE NOTICE 'Usuario $reader_user creado';
  ELSE
    ALTER USER $reader_user WITH PASSWORD '$DB_READER_PASSWORD';
    RAISE NOTICE 'Contraseña de $reader_user actualizada';
  END IF;
END
\$\$;"

  # 3. Crear usuario writer si no existe y asignar contraseña
  run_sql "postgres" "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$writer_user') THEN
    CREATE USER $writer_user WITH LOGIN PASSWORD '$DB_WRITER_PASSWORD';
    RAISE NOTICE 'Usuario $writer_user creado';
  ELSE
    ALTER USER $writer_user WITH PASSWORD '$DB_WRITER_PASSWORD';
    RAISE NOTICE 'Contraseña de $writer_user actualizada';
  END IF;
END
\$\$;"

  # 4. Asignar roles a los usuarios
  run_sql "postgres" "
    GRANT hiluca_readonly  TO $reader_user;
    GRANT hiluca_readwrite TO $writer_user;
  "

  # 5. Permisos en la base de datos específica
  run_sql "$db_name" "
    -- Conectarse a la DB
    GRANT CONNECT ON DATABASE $db_name TO hiluca_readonly;
    GRANT CONNECT ON DATABASE $db_name TO hiluca_readwrite;

    -- Permisos en el schema public
    GRANT USAGE ON SCHEMA public TO hiluca_readonly;
    GRANT USAGE ON SCHEMA public TO hiluca_readwrite;

    -- hiluca_readonly: solo SELECT
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO hiluca_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT SELECT ON TABLES TO hiluca_readonly;

    -- hiluca_readwrite: SELECT + INSERT + UPDATE + DELETE
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hiluca_readwrite;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hiluca_readwrite;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hiluca_readwrite;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT USAGE, SELECT ON SEQUENCES TO hiluca_readwrite;
  "

  echo "  ✓ $db_name: $reader_user (readonly) y $writer_user (readwrite) configurados"
}

# ── Provisionar cada base de datos ───────────────────────────────────────────
provision_database "$DB_NAME_STRAPI"
provision_database "$DB_NAME_SINERGIA"

# ── Marcar como ejecutado (idempotencia) ─────────────────────────────────────
mkdir -p "$(dirname "$SENTINEL")"
touch "$SENTINEL"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  init_db_users.sh – Provisioning completado                     ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Roles creados:                                                  ║"
echo "║    hiluca_readonly  → SELECT                                     ║"
echo "║    hiluca_readwrite → SELECT, INSERT, UPDATE, DELETE             ║"
echo "║                                                                  ║"
printf "║  DB: %-57s║\n" "$DB_NAME_STRAPI"
printf "║    %s_reader (readonly)\n" "$DB_NAME_STRAPI"
printf "║    %s_writer (readwrite)\n" "$DB_NAME_STRAPI"
printf "║  DB: %-57s║\n" "$DB_NAME_SINERGIA"
printf "║    %s_reader (readonly)\n" "$DB_NAME_SINERGIA"
printf "║    %s_writer (readwrite)\n" "$DB_NAME_SINERGIA"
echo "╚══════════════════════════════════════════════════════════════════╝"
