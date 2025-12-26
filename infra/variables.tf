# ---------------------------------------------------------------------------------------------
# Variables -----------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

variable "organisation_id" {
  description = "Organization ID in Google Cloud Platform"
  type        = string
  nullable    = false
  sensitive   = true
}

variable "project_id" {
  description = "Project ID in Google Cloud Platform"
  type        = string
  nullable    = false
  sensitive   = true
}

variable "project_region" {
  description = "Default region for Google Cloud Platform resources"
  type        = string
  nullable    = false
  sensitive   = true
}
