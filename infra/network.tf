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

resource "google_compute_firewall" "allow_ssh_from_internet" {
  name      = "fw-allow-ssh-from-internet"
  direction = "INGRESS"
  network   = google_compute_network.measurement.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["allow-ssh"]
}

resource "google_compute_firewall" "focus_probe" {
  name      = "fw-focus-probe"
  direction = "INGRESS"
  network   = google_compute_network.measurement.name

  allow {
    protocol = "tcp"
    ports    = ["22", "8888"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["probe"]
}

resource "google_compute_firewall" "focus_target" {
  name      = "fw-focus-target"
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
    ports    = ["5353"]
  }

  source_tags = ["probe"]
  target_tags = ["target"]
}
