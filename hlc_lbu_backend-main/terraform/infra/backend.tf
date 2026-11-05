# ══════════════════════════════════════════════════════════════════════════════
# backend.tf – GCS Remote State
#
# El bucket DEBE existir antes del primer `terraform init`.
# Créalo una sola vez con:
#   bash bootstrap/create-state-bucket.sh
#
# Flujo por ambiente (usando Terraform Workspaces):
#   terraform workspace new dev   (solo la primera vez)
#   terraform workspace select dev
#   terraform init
#   terraform apply -var-file=env/dev.tfvars
#
# Estado guardado en GCS:
#   dev → gs://hiluca-lbu-tf-state/infra/dev.tfstate
#   qas → gs://hiluca-lbu-tf-state/infra/qas.tfstate
#   prd → gs://hiluca-lbu-tf-state/infra/prd.tfstate
# ══════════════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "hiluca-lbu-tf-state"
    prefix = "infra"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
