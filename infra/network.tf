# ---------------------------------------------------------------------------------------------
# Network -------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_compute_network" "measurement" {
  name                    = "vpc-network-measurement"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "measurement" {
  name          = "measurement-subnet"
  region        = var.project_region
  network       = google_compute_network.measurement.id
  ip_cidr_range = "10.20.0.0/16"

  private_ip_google_access = true

  depends_on = [
    google_compute_network.measurement,
  ]
}

resource "google_compute_firewall" "internet_to_probe_http" {
  name      = "allow-internet-to-probe-8888"
  direction = "INGRESS"
  network   = google_compute_network.measurement.name


  allow {
    protocol = "tcp"
    ports    = ["22", "8888"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["probe"]
}

resource "google_compute_firewall" "probe_to_target_latency" {
  name      = "allow-probe-to-target-latency"
  direction = "INGRESS"
  network   = google_compute_network.measurement.name


  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["22", "9999"]
  }

  allow {
    protocol = "udp"
    ports    = ["53"]
  }

  source_tags = ["probe"]
  target_tags = ["target"]
}
