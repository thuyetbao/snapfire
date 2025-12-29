# ---------------------------------------------------------------------------------------------
# IAM -----------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------
# Service Account: Largo ----------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_service_account" "sa_largo" {
  account_id   = "sa-largo"
  display_name = "SA Largo"
  description  = "Largo - Strums music to empower allies and can dispel with a lick"
}

resource "google_project_iam_member" "sa_largo" {
  for_each = toset([
    "roles/compute.instanceAdmin.v1",
    "roles/artifactregistry.reader",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/serviceusage.serviceUsageViewer",
    "roles/serviceusage.serviceUsageConsumer",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.sa_largo.email}"

  depends_on = [
    google_service_account.sa_largo,
  ]
}

# ---------------------------------------------------------------------------------------------
# Service Account: Ringmaster -----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_service_account" "sa_ringmaster" {
  account_id   = "sa-ringmaster"
  display_name = "SA Ringmaster"
  description  = "Ringmaster - Directs the battle with fear and mesmerism"
}

resource "google_project_iam_member" "sa_ringmaster" {
  for_each = toset([
    "roles/compute.instanceAdmin.v1",
    "roles/artifactregistry.reader",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/serviceusage.serviceUsageViewer",
    "roles/serviceusage.serviceUsageConsumer",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.sa_ringmaster.email}"

  depends_on = [
    google_service_account.sa_ringmaster,
  ]
}
