//! # phenotype-vessel
//!
//! Container image management.

use serde::{Deserialize, Serialize};

/// Container image representation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Image {
    /// Image ID (digest or hash)
    pub id: String,
    /// Image name
    pub name: String,
    /// Image tag
    pub tag: String,
    /// Image size in bytes
    pub size: u64,
}

/// Image pull progress information
#[derive(Debug, Clone)]
pub struct ImagePullProgress {
    /// Status message
    pub status: String,
    /// Progress percentage (if available)
    pub progress: Option<f32>,
    /// Download speed (bytes/sec)
    pub speed: Option<u64>,
}

impl Image {
    /// Create a new image reference
    pub fn new(name: &str) -> Self {
        let parts: Vec<&str> = name.split(':').collect();
        Self {
            id: name.to_string(),
            name: parts.first().unwrap_or(&name).to_string(),
            tag: parts.get(1).unwrap_or(&"latest").to_string(),
            size: 0,
        }
    }

    /// Full image reference (name:tag)
    pub fn reference(&self) -> String {
        format!("{}:{}", self.name, self.tag)
    }

    /// Check if this is a digest reference
    pub fn is_digest(&self) -> bool {
        self.tag.starts_with("sha256:")
    }
}

impl std::fmt::Display for Image {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}", self.name, self.tag)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_image_creation() {
        let image = Image::new("nginx:latest");
        assert_eq!(image.name, "nginx");
        assert_eq!(image.tag, "latest");
    }

    #[test]
    fn test_image_reference() {
        let image = Image::new("postgres:15");
        assert_eq!(image.reference(), "postgres:15");
    }

    #[test]
    fn test_digest_image() {
        let image = Image {
            id: "sha256:abc123".to_string(),
            name: "nginx".to_string(),
            tag: "sha256:abc123".to_string(),
            size: 100,
        };
        assert!(image.is_digest());
    }

    #[test]
    fn test_image_is_digest_false() {
        let image = Image::new("alpine");
        assert_eq!(image.name, "alpine");
        assert_eq!(image.tag, "latest");
        assert!(!image.is_digest());

        let image = Image::new("ubuntu:20.04");
        assert_eq!(image.name, "ubuntu");
        assert_eq!(image.tag, "20.04");
        assert!(!image.is_digest());
    }

    #[test]
    fn test_image_display() {
        let image = Image {
            id: "alpine:3.18".to_string(),
            name: "alpine".to_string(),
            tag: "3.18".to_string(),
            size: 0,
        };
        assert_eq!(format!("{}", image), "alpine:3.18");

        let digest_image = Image {
            id: "nginx:sha256:abcdef".to_string(),
            name: "nginx".to_string(),
            tag: "sha256:abcdef".to_string(),
            size: 0,
        };
        assert_eq!(format!("{}", digest_image), "nginx:sha256:abcdef");
    }

    #[test]
    fn test_image_serde_roundtrip() {
        let image = Image {
            id: "nginx:1.25-alpine".to_string(),
            name: "nginx".to_string(),
            tag: "1.25-alpine".to_string(),
            size: 42,
        };
        // Use serde_yaml (already a dev-dep) to validate the Serialize/Deserialize
        // derives on Image round-trip cleanly. The on-the-wire format is irrelevant
        // for verifying derive correctness on this all-primitive field set.
        let serialized = serde_yaml::to_string(&image).expect("serialize Image");
        let parsed: Image = serde_yaml::from_str(&serialized).expect("deserialize Image");
        assert_eq!(parsed.id, "nginx:1.25-alpine");
        assert_eq!(parsed.name, "nginx");
        assert_eq!(parsed.tag, "1.25-alpine");
        assert_eq!(parsed.size, 42);
    }

    #[test]
    fn test_image_new_defaults() {
        let alpine = Image::new("alpine");
        assert_eq!(alpine.name, "alpine");
        assert_eq!(alpine.tag, "latest");
        assert_eq!(alpine.id, "alpine");
        assert_eq!(alpine.size, 0);

        let redis = Image::new("redis");
        assert_eq!(redis.name, "redis");
        assert_eq!(redis.tag, "latest");
        assert_eq!(redis.id, "redis");
        assert_eq!(redis.size, 0);

        let postgres = Image::new("postgres:15");
        assert_eq!(postgres.name, "postgres");
        assert_eq!(postgres.tag, "15");
        assert_eq!(postgres.id, "postgres:15");
        assert_eq!(postgres.size, 0);
    }

    #[test]
    fn test_image_pull_progress() {
        let mut progress = ImagePullProgress {
            status: "Downloading".to_string(),
            progress: Some(0.5),
            speed: Some(1_000_000),
        };
        assert_eq!(progress.status, "Downloading");
        assert_eq!(progress.progress, Some(0.5));
        assert_eq!(progress.speed, Some(1_000_000));

        progress.status = "Extracting".to_string();
        progress.progress = Some(1.0);
        progress.speed = None;
        assert_eq!(progress.status, "Extracting");
        assert_eq!(progress.progress, Some(1.0));
        assert_eq!(progress.speed, None);
    }

    #[test]
    fn test_image_equality_via_fields() {
        // Image does not derive PartialEq, so compare field-by-field.
        let a = Image {
            id: "nginx:1.25".to_string(),
            name: "nginx".to_string(),
            tag: "1.25".to_string(),
            size: 100,
        };
        let b = Image {
            id: "nginx:1.25".to_string(),
            name: "nginx".to_string(),
            tag: "1.25".to_string(),
            size: 100,
        };
        assert_eq!(a.id, b.id);
        assert_eq!(a.name, b.name);
        assert_eq!(a.tag, b.tag);
        assert_eq!(a.size, b.size);

        // Differing Images diverge in at least one field.
        let different_size = Image {
            id: "nginx:1.25".to_string(),
            name: "nginx".to_string(),
            tag: "1.25".to_string(),
            size: 200,
        };
        assert_ne!(a.size, different_size.size);

        let different_tag = Image {
            id: "nginx:1.26".to_string(),
            name: "nginx".to_string(),
            tag: "1.26".to_string(),
            size: 100,
        };
        assert_ne!(a.tag, different_tag.tag);
    }

    #[test]
    fn test_image_new_with_multi_colon_tag() {
        // `Image::new` performs a naive `split(':')`, so a registry with a
        // port and a tag will parse the port as the "tag". This documents
        // the parser's behavior; callers wanting port-aware parsing must
        // pre-strip or post-validate.
        let image = Image::new("registry.example.com:5000/myapp:v1.2.3");
        assert_eq!(image.name, "registry.example.com");
        assert_eq!(image.tag, "5000/myapp");
        assert_eq!(image.id, "registry.example.com:5000/myapp:v1.2.3");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_new_with_empty_name() {
        // A leading colon yields an empty name and the suffix as the tag.
        let image = Image::new(":latest");
        assert_eq!(image.name, "");
        assert_eq!(image.tag, "latest");
        assert_eq!(image.id, ":latest");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_reference_with_digest() {
        // `reference()` simply joins name and tag with ':', so a digest-style
        // tag yields a multi-colon reference.
        let image = Image {
            id: "nginx:sha256:abc".to_string(),
            name: "nginx".to_string(),
            tag: "sha256:abc".to_string(),
            size: 0,
        };
        assert_eq!(image.reference(), "nginx:sha256:abc");
    }

    #[test]
    fn test_image_debug_format() {
        // `Image` derives `Debug`, so formatting with `{:?}` must include
        // both the `name` and `tag` field names verbatim.
        let image = Image::new("nginx:1.25");
        let debug = format!("{:?}", image);
        assert!(debug.contains("name"), "Debug output missing `name`: {debug}");
        assert!(debug.contains("tag"), "Debug output missing `tag`: {debug}");
        assert!(debug.contains("nginx"), "Debug output missing value `nginx`: {debug}");
        assert!(debug.contains("1.25"), "Debug output missing value `1.25`: {debug}");
    }

    #[test]
    fn test_image_pull_progress_default_construction() {
        // `ImagePullProgress` has no `Default` derive, but it can be
        // constructed with empty/None fields.
        let progress = ImagePullProgress {
            status: String::new(),
            progress: None,
            speed: None,
        };
        assert_eq!(progress.status, "");
        assert!(progress.status.is_empty());
        assert_eq!(progress.progress, None);
        assert_eq!(progress.speed, None);
    }

    #[test]
    fn test_image_new_with_simple_name() {
        // A bare name with no ':' yields the name itself and defaults the tag to "latest".
        let image = Image::new("nginx");
        assert_eq!(image.name, "nginx");
        assert_eq!(image.tag, "latest");
        assert_eq!(image.id, "nginx");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_new_with_name_and_tag() {
        // `Image::new` splits on the first ':' to separate name and tag.
        let image = Image::new("nginx:1.25");
        assert_eq!(image.name, "nginx");
        assert_eq!(image.tag, "1.25");
        assert_eq!(image.id, "nginx:1.25");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_new_with_name_and_digest() {
        // The constructor splits on ':' only, so a digest ref like
        // `nginx@sha256:abc` yields the literal `@`-prefixed name and `abc` as
        // the tag. The full input is preserved in `id`, which is what callers
        // can use to recover the digest.
        let image = Image::new("nginx@sha256:abc");
        assert_eq!(image.id, "nginx@sha256:abc");
        assert!(image.id.contains("sha256"), "id must contain the digest: {}", image.id);
        // Document the actual parser behavior (no special handling of '@').
        assert_eq!(image.name, "nginx@sha256");
        assert_eq!(image.tag, "abc");
    }

    #[test]
    fn test_image_new_with_complex_name() {
        // Path-style name with a version+variant tag stays split on the first ':'.
        let image = Image::new("library/nginx:1.25-alpine");
        assert_eq!(image.name, "library/nginx");
        assert_eq!(image.tag, "1.25-alpine");
        assert_eq!(image.id, "library/nginx:1.25-alpine");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_new_with_registry_prefix() {
        // A fully qualified registry/library/name:tag reference — the entire
        // `docker.io/library/nginx` path stays in `name` and the tag is `latest`.
        let image = Image::new("docker.io/library/nginx:latest");
        assert_eq!(image.name, "docker.io/library/nginx");
        assert_eq!(image.tag, "latest");
        assert_eq!(image.id, "docker.io/library/nginx:latest");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_new_with_no_tag_returns_latest() {
        // A bare name (no ':') yields tag == "latest" via the default branch.
        let image = Image::new("alpine");
        assert_eq!(image.name, "alpine");
        assert_eq!(image.tag, "latest");
        assert_eq!(image.id, "alpine");
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_with_empty_tag() {
        // Manually constructing an Image with an empty tag — `is_digest()` must
        // return false because an empty string does not start with "sha256:".
        let image = Image {
            id: "nginx".to_string(),
            name: "nginx".to_string(),
            tag: String::new(),
            size: 0,
        };
        assert!(image.tag.is_empty());
        assert!(!image.is_digest(), "empty tag must not be classified as a digest");
    }

    #[test]
    fn test_image_display_with_digest() {
        // `Display` writes `name:tag`, so a digest-style tag yields a
        // multi-colon reference. The rendered output must contain the digest
        // prefix verbatim.
        let image = Image {
            id: "sha256:abcdef0123456789".to_string(),
            name: "nginx".to_string(),
            tag: "sha256:abcdef0123456789".to_string(),
            size: 0,
        };
        let displayed = format!("{}", image);
        assert!(
            displayed.contains("sha256:abc"),
            "Display must contain digest prefix, got: {displayed}"
        );
        assert!(displayed.contains("nginx"), "Display must contain name, got: {displayed}");
        assert_eq!(displayed, "nginx:sha256:abcdef0123456789");
    }

    #[test]
    fn test_image_with_zero_size() {
        // A manually constructed image with size 0 must preserve it (no
        // normalization, no overflow, no defaulting).
        let image = Image {
            id: "alpine:3.18".to_string(),
            name: "alpine".to_string(),
            tag: "3.18".to_string(),
            size: 0,
        };
        assert_eq!(image.size, 0);
    }

    #[test]
    fn test_image_with_huge_size() {
        // The size field is u64; u64::MAX must round-trip with no overflow
        // check and no clamping.
        let image = Image {
            id: "huge:latest".to_string(),
            name: "huge".to_string(),
            tag: "latest".to_string(),
            size: u64::MAX,
        };
        assert_eq!(image.size, u64::MAX);
    }

    #[test]
    fn test_image_pull_progress_with_all_fields() {
        // All three fields populated — preserve each verbatim.
        let progress = ImagePullProgress {
            status: "Downloading".to_string(),
            progress: Some(0.75),
            speed: Some(2_500_000),
        };
        assert_eq!(progress.status, "Downloading");
        assert_eq!(progress.progress, Some(0.75));
        assert_eq!(progress.speed, Some(2_500_000));
    }

    #[test]
    fn test_image_pull_progress_with_only_status() {
        // Only the required `status` is set; both Options are None.
        let progress = ImagePullProgress {
            status: "downloading".to_string(),
            progress: None,
            speed: None,
        };
        assert_eq!(progress.status, "downloading");
        assert_eq!(progress.progress, None);
        assert_eq!(progress.speed, None);
    }
}
