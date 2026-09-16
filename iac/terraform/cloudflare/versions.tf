# versions.tf — pin the Cloudflare provider source for this module.
#
# Unlike oci/google/aws, the Cloudflare provider does NOT live under the
# default `hashicorp/` namespace, so `terraform validate` on this module in
# isolation (as the terraform-plan CI matrix runs it) fails with
# "Missing required provider registry.terraform.io/hashicorp/cloudflare"
# unless the correct source is declared here. Version mirrors the root
# providers.tf pin.
terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.18"
    }
  }
}
