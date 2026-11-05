# ══════════════════════════════════════════════════════════════════════════════
# backend.tf – ADK Multi-Agent Service
#
# Remote state stored in the same GCS bucket as the rest of the project.
# State path: gs://hiluca-lbu-tf-state/adk/terraform.tfstate
#
# First-time setup:
#   terraform init
#   terraform apply -var-file=terraform.tfvars
#
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
    prefix = "adk"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
