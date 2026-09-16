# e2-micro.tf — gcp-e2 tertiary runner + uptime sentinel.

variable "gcp_project_id" { type = string /* <GCP_PROJECT_ID> */ }
variable "gcp_region" {
  type    = string
  default = "us-west1"
}
variable "gcp_zone" {
  type    = string
  default = "us-west1-b"
}
variable "gcp_sa_key_path" { type = string }
variable "gcp_ssh_public_key" { type = string }

provider "google" {
  project     = var.gcp_project_id
  region      = var.gcp_region
  zone        = var.gcp_zone
  credentials = file(var.gcp_sa_key_path)
}

# resource "google_compute_instance" "gcp_e2" {
#   name         = "gcp-e2"
#   machine_type = "e2-micro"
#   zone         = var.gcp_zone
#
#   boot_disk {
#     initialize_params {
#       image = "ubuntu-os-cloud/ubuntu-2404-lts"
#       size  = 30
#     }
#   }
#
#   network_interface {
#     network = "default"
#     access_config {}  # temp public IP for cloud-init; remove after Tailscale up
#   }
#
#   metadata = {
#     ssh-keys  = "ubuntu:${var.gcp_ssh_public_key}"
#     user-data = templatefile("${path.module}/cloud-init.yaml", {
#       tailscale_authkey = "<TAILSCALE_AUTHKEY>"
#     })
#   }
# }
