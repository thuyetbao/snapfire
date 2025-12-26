# ---------------------------------------------------------------------------------------------
# Outputs -------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

output "latency_app_public_ip" {
  value       = google_compute_instance.latency_app.network_interface[0].access_config[0].nat_ip
  description = "Public IP of the latency application VM"
}

output "latency_target_private_ip" {
  value       = google_compute_instance.latency_target.network_interface[0].network_ip
  description = "Private IP of the latency target VM"
}
