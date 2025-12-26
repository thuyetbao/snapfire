# ---------------------------------------------------------------------------------------------
# Terraform Configuration ---------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

terraform {
  required_version = "~> 1.10.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.project_region

  default_labels = {
    environment             = "production"
    managed_by              = "terraform"
    google_provider_variant = "stable"
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.project_region

  default_labels = {
    environment             = "production"
    managed_by              = "terraform"
    google_provider_variant = "beta"
  }
}

# Search by: `gcloud services list --available | grep .googleapis.com`
# Validate by: `gcloud services list --enabled`
resource "google_project_service" "discovery_mesh" {
  for_each = toset([
    "vpcaccess.googleapis.com",
    "networksecurity.googleapis.com",
    "servicenetworking.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
  ])
  project = var.project_id
  service = each.key

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true

  # Do not disable the service on destroy. On destroy, we are going to
  # destroy the project, but we need the APIs available to destroy the
  # underlying resources.
  disable_on_destroy = false
}

# The numeric identifier of the project
# See: https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/project
data "google_project" "snapfire" {
  project_id = var.project_id
}
