# ---------------------------------------------------------------------------------------------
# Compute Engine ------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------
# CE: Probe -----------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_compute_instance" "alien_probe" {
  project      = var.project_id
  zone         = "${var.project_region}-a"
  name         = "alien-probe"
  description  = "The latency application probe instance"
  machine_type = "e2-micro"

  boot_disk {
    initialize_params {
      image = "projects/cos-cloud/global/images/family/cos-stable"
    }
  }

  network_interface {
    network    = google_compute_network.measurement.id
    subnetwork = google_compute_subnetwork.measurement.id
    access_config {} # ephemeral external IP
  }

  metadata = {
    user-data = templatefile("./instance/probe.yaml", {
      c_requirement_txt       = file("../provision/probe/requirements.txt")
      c_application_agent     = file("../provision/probe/agent.py")
      c_application_collector = file("../provision/probe/collector.py")
      DESTINATION_IP          = google_compute_instance.alien_target.network_interface[0].network_ip
    })
  }

  service_account {
    email  = google_service_account.sa_largo.email
    scopes = ["cloud-platform"]
  }

  tags = ["probe"]

  depends_on = [google_compute_instance.alien_target]
}

# ---------------------------------------------------------------------------------------------
# CE: Target ----------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_compute_instance" "alien_target" {
  project      = var.project_id
  zone         = "${var.project_region}-a"
  name         = "alien-target"
  description  = "The latency application target instance"
  machine_type = "e2-micro"

  boot_disk {
    initialize_params {
      image = "projects/cos-cloud/global/images/family/cos-stable"
    }
  }

  network_interface {
    network    = google_compute_network.measurement.id
    subnetwork = google_compute_subnetwork.measurement.id
    # access_config {}
  }

  metadata = {
    user-data = templatefile("./instance/target.yaml", {
      c_requirement_txt     = file("../provision/target/requirements.txt")
      c_application_exposer = file("../provision/target/exposer.py")
    })
  }

  service_account {
    email  = google_service_account.sa_largo.email
    scopes = ["cloud-platform"]
  }

  tags = ["target"]
}
