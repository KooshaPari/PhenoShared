# tunnel.tf — Cloudflare Tunnel from edge to oci-primary.

variable "cloudflare_account_id" { type = string /* <CLOUDFLARE_ACCOUNT_ID> */ }
variable "cloudflare_zone_id" { type = string /* <CLOUDFLARE_ZONE_ID> */ }
variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# resource "cloudflare_tunnel" "oci_primary" {
#   account_id = var.cloudflare_account_id
#   name       = "oci-primary"
#   secret     = random_password.tunnel_secret.result
# }
#
# resource "cloudflare_record" "git" {
#   zone_id = var.cloudflare_zone_id
#   name    = "git"
#   value   = "${cloudflare_tunnel.oci_primary.id}.cfargotunnel.com"
#   type    = "CNAME"
#   proxied = true
# }
#
# resource "cloudflare_record" "vault" {
#   zone_id = var.cloudflare_zone_id
#   name    = "vault"
#   value   = "${cloudflare_tunnel.oci_primary.id}.cfargotunnel.com"
#   type    = "CNAME"
#   proxied = true
# }
#
# resource "cloudflare_record" "ci" {
#   zone_id = var.cloudflare_zone_id
#   name    = "ci"
#   value   = "${cloudflare_tunnel.oci_primary.id}.cfargotunnel.com"
#   type    = "CNAME"
#   proxied = true
# }
