# workers.tf — Cloudflare Workers for edge routing / maintenance page / (Phase 2) R2 registry proxy.

# resource "cloudflare_worker_script" "maintenance" {
#   account_id = var.cloudflare_account_id
#   name       = "maintenance"
#   content    = file("${path.module}/workers/maintenance.js")
# }
#
# resource "cloudflare_worker_route" "maintenance" {
#   zone_id     = var.cloudflare_zone_id
#   pattern     = "maint.phenotype.io/*"
#   script_name = cloudflare_worker_script.maintenance.name
# }
#
# Phase 2: r2-registry-proxy Worker + R2 bucket bindings.
