terraform {
  required_version = ">=1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

#firewall :ssh only

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-sre"
  network = "default"
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["sre-demo"]
}
#e2-micro in gcp is free

resource "google_compute_instance" "demo_vm" {
  name         = "sre-agent-demo-vm"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 10
      type  = "pd-standard"
    }
  }
  network_interface {
    network = "default"
    access_config {} #ephermeral public ip
  }
  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.public_key_path)}"
  }
  tags = ["sre-demo"]
  service_account {
    scopes = ["cloud-platform"]
  }
}
