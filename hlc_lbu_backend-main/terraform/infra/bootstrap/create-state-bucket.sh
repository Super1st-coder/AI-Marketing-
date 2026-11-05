#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# bootstrap/create-state-bucket.sh
#
# Crea el bucket de GCS para el estado remoto de Terraform.
# Ejecutar UNA SOLA VEZ antes del primer `terraform init`.
#
# Uso:
#   bash bootstrap/create-state-bucket.sh
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="careful-acumen-422922-k4"
BUCKET_NAME="hiluca-lbu-tf-state"
REGION="us-central1"

echo "==> Creando bucket de Terraform state: gs://$BUCKET_NAME"

# Crear el bucket con acceso uniforme y sin acceso público
gcloud storage buckets create "gs://$BUCKET_NAME" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --public-access-prevention

# Habilitar versionado para poder recuperar estados anteriores
gcloud storage buckets update "gs://$BUCKET_NAME" \
  --versioning

echo ""
echo "Bucket creado: gs://$BUCKET_NAME"
echo ""
echo "Próximos pasos por ambiente:"
echo ""
echo "  # Dev"
echo "  terraform workspace new dev"
echo "  terraform init"
echo "  terraform apply -var-file=env/dev.tfvars"
echo ""
echo "  # QAS"
echo "  terraform workspace new qas"
echo "  terraform init"
echo "  terraform apply -var-file=env/qas.tfvars"
echo ""
echo "  # Producción"
echo "  terraform workspace new prd"
echo "  terraform init"
echo "  terraform apply -var-file=env/prd.tfvars"
