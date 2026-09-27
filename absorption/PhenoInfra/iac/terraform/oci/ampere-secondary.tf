# ampere-secondary.tf — oci-secondary VM (CI agent + metrics + backup target).
# Stub: mirrors ampere-primary.tf with distinct display_name and cloud-init.

# resource "oci_core_instance" "oci_secondary" {
#   compartment_id      = var.oci_compartment_ocid
#   availability_domain = data.oci_identity_availability_domain.ad1.name
#   shape               = "VM.Standard.A1.Flex"
#   shape_config { ocpus = 2; memory_in_gbs = 12 }
#   display_name = "oci-secondary"
#
#   create_vnic_details {
#     subnet_id        = oci_core_subnet.mesh_public.id
#     assign_public_ip = false
#   }
#
#   source_details {
#     source_type = "image"
#     source_id   = data.oci_core_images.ubuntu_2404_arm.images[0].id
#   }
#
#   metadata = {
#     ssh_authorized_keys = var.oci_ssh_public_key
#     user_data           = base64encode(templatefile("${path.module}/cloud-init/secondary.yaml", {
#       tailscale_authkey = tailscale_tailnet_key.oci_secondary.key
#     }))
#   }
# }
