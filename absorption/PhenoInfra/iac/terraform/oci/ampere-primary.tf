# ampere-primary.tf — oci-primary VM (Forgejo + Vaultwarden + Woodpecker server).
# Stub: resource blocks commented out until first-apply review.

variable "oci_tenancy_ocid" { type = string /* <OCI_TENANCY_OCID> */ }
variable "oci_user_ocid" { type = string /* <OCI_USER_OCID> */ }
variable "oci_fingerprint" {
  type      = string
  sensitive = true
}
variable "oci_private_key_path" { type = string }
variable "oci_region" {
  type    = string
  default = "us-phoenix-1"
}
variable "oci_compartment_ocid" { type = string }
variable "oci_ssh_public_key" { type = string }

provider "oci" {
  tenancy_ocid     = var.oci_tenancy_ocid
  user_ocid        = var.oci_user_ocid
  fingerprint      = var.oci_fingerprint
  private_key_path = var.oci_private_key_path
  region           = var.oci_region
}

# resource "oci_core_vcn" "mesh" {
#   compartment_id = var.oci_compartment_ocid
#   cidr_blocks    = ["10.0.0.0/16"]
#   display_name   = "phenotype-mesh-vcn"
# }
#
# resource "oci_core_subnet" "mesh_public" {
#   compartment_id = var.oci_compartment_ocid
#   vcn_id         = oci_core_vcn.mesh.id
#   cidr_block     = "10.0.1.0/24"
#   display_name   = "mesh-public"
# }
#
# resource "oci_core_instance" "oci_primary" {
#   compartment_id      = var.oci_compartment_ocid
#   availability_domain = data.oci_identity_availability_domain.ad1.name
#   shape               = "VM.Standard.A1.Flex"
#   shape_config { ocpus = 2; memory_in_gbs = 12 }
#   display_name = "oci-primary"
#
#   create_vnic_details {
#     subnet_id        = oci_core_subnet.mesh_public.id
#     assign_public_ip = false   # Tailscale only; CF Tunnel provides public surface
#   }
#
#   source_details {
#     source_type = "image"
#     source_id   = data.oci_core_images.ubuntu_2404_arm.images[0].id
#   }
#
#   metadata = {
#     ssh_authorized_keys = var.oci_ssh_public_key
#     user_data           = base64encode(templatefile("${path.module}/cloud-init/primary.yaml", {
#       tailscale_authkey = tailscale_tailnet_key.oci_primary.key
#     }))
#   }
# }
#
# output "oci_primary_private_ip" {
#   value = oci_core_instance.oci_primary.private_ip
# }
