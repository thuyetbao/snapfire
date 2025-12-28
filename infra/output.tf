# ---------------------------------------------------------------------------------------------
# Outputs -------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

output "probe_public_ip" {
  value       = google_compute_instance.alien_probe.network_interface[0].access_config[0].nat_ip
  description = "Public IP of the probe VM"
}

output "target_private_ip" {
  value       = google_compute_instance.alien_target.network_interface[0].network_ip
  description = "Private IP of the target VM"
}
