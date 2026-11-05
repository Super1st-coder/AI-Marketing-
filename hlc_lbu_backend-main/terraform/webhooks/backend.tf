# ══════════════════════════════════════════════════════════════════════════════
# backend.tf – HiLuca Webhook Gateway Infrastructure
#
# Estado en GCS (mismo bucket que infra/, prefijo separado):
#   gs://hiluca-lbu-tf-state/webhooks/terraform.tfstate
#
# Inicializar:
#   cd terraform/webhooks
#   terraform init
#   terraform apply -var-file=terraform.tfvars
# ══════════════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "hiluca-lbu-tf-state"
    prefix = "webhooks"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
