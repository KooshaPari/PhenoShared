# providers.tf — version-pinned provider declarations for the 7-node mesh.
# Real creds come from TF_VAR_* env vars sourced via `bw get notes <provider>/terraform-env`.

terraform {
  required_version = ">= 1.7"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 9.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 8.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.42"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.18"
    }
    tailscale = {
      source  = "tailscale/tailscale"
      version = "~> 0.16"
    }
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.47"
    }
  }

  # backend omitted: state is snapshotted to Vaultwarden, not S3.
  # Each top-level module (oci/, gcp/, aws/, cloudflare/) may declare its own backend later if remote state becomes necessary.
}

# provider blocks intentionally unset here — each module declares its own with scoped credentials.
