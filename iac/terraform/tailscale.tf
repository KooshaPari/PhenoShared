# tailscale.tf — ephemeral auth-key generation for mesh nodes.
# Real values injected via TF_VAR_tailscale_oauth_client_{id,secret}.

variable "tailscale_tailnet" {
  description = "Tailscale tailnet identifier (e.g. <email>@github or <org>.ts.net)"
  type        = string
  # default = "<TAILSCALE_TAILNET>"
}

variable "tailscale_oauth_client_id" {
  type      = string
  sensitive = true
}

variable "tailscale_oauth_client_secret" {
  type      = string
  sensitive = true
}

provider "tailscale" {
  tailnet             = var.tailscale_tailnet
  oauth_client_id     = var.tailscale_oauth_client_id
  oauth_client_secret = var.tailscale_oauth_client_secret
}

# Ephemeral auth keys issued per-node at provision time.
# TTL = 3600 (1 hour) — key is consumed by cloud-init; node registers itself.
#
# resource "tailscale_tailnet_key" "oci_primary" {
#   reusable      = false
#   ephemeral     = false
#   preauthorized = true
#   expiry        = 3600
#   description   = "oci-primary bring-up"
#   tags          = ["tag:backbone"]
# }
#
# resource "tailscale_tailnet_key" "home_mac" {
#   reusable      = false
#   ephemeral     = false
#   preauthorized = true
#   expiry        = 86400  # 24h for home provisioning window
#   description   = "home-mac registration"
#   tags          = ["tag:home"]
# }

# ACL document is managed separately via tailscale_acl resource:
#
# resource "tailscale_acl" "main" {
#   acl = jsonencode({
#     acls = [
#       { action = "accept", src = ["tag:runner"], dst = ["tag:backbone:9000"] },
#       { action = "accept", src = ["tag:backbone"], dst = ["tag:backbone:*"] },
#       { action = "accept", src = ["autogroup:admin"], dst = ["*:22"] },
#       { action = "accept", src = ["tag:home"], dst = ["tag:backbone:9000"] },
#     ]
#     tagOwners = {
#       "tag:backbone" = ["autogroup:admin"]
#       "tag:runner"   = ["autogroup:admin"]
#       "tag:home"     = ["autogroup:admin"]
#       "tag:burst"    = ["autogroup:admin"]
#     }
#   })
# }
