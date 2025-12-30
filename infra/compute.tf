# ---------------------------------------------------------------------------------------------
# Compute Engine ------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------
# CE: Probe -----------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_compute_instance" "probe" {
  project      = var.project_id
  zone         = "${var.project_region}-a"
  name         = "friend-probe"
  description  = "The snapfire friend - Probe member"
  machine_type = "e2-micro"
  tags         = ["probe", "allow-ssh"]

  boot_disk {
    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
    }
  }

  network_interface {
    network    = google_compute_network.horizon_space.id
    subnetwork = google_compute_subnetwork.horizon_space_public.id
    access_config {}
  }

  service_account {
    email  = google_service_account.sa_largo.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    user-data = templatefile("./instance/probe.yaml.tftpl", {
      c_requirement_txt       = file("../provision/probe/requirements.txt")
      c_application_agent     = file("../provision/probe/agent.py")
      c_application_collector = file("../provision/probe/collector.py")
      DESTINATION_IP          = google_compute_instance.target.network_interface[0].network_ip
    })
  }

  depends_on = [
    google_compute_instance.target
  ]
}

# ---------------------------------------------------------------------------------------------
# CE: Target ----------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

resource "google_compute_instance" "target" {
  project      = var.project_id
  zone         = "${var.project_region}-a"
  name         = "friend-target"
  description  = "The snapfire friend - Target member"
  machine_type = "e2-micro"
  tags         = ["target", "allow-ssh"]

  boot_disk {
    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
    }
  }

  network_interface {
    network    = google_compute_network.horizon_space.id
    subnetwork = google_compute_subnetwork.horizon_space_public.id
    access_config {}
  }

  service_account {
    email  = google_service_account.sa_largo.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    user-data = templatefile("./instance/target.yaml.tftpl", {
      c_requirement_txt     = file("../provision/target/requirements.txt")
      c_application_exposer = file("../provision/target/exposer.py")
    })
  }
}
