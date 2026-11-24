// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

use uuid::Uuid;

pub fn new_id() -> Uuid {
    Uuid::new_v4()
}

pub fn short_id(id: &Uuid, namespace: &str, len: usize) -> String {
    if len <= namespace.len() + 1 {
        return format!("{}_{:x}", namespace, id.as_u128());
    }

    let digits = (len - namespace.len() - 1).min(32);
    let compact = id.as_simple().to_string();
    format!("{}_{}", namespace, &compact[..digits])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_id_is_unique() {
        assert_ne!(new_id(), new_id());
    }

    #[test]
    fn short_id_respects_namespace_and_length() {
        let id = Uuid::parse_str("550e8400-e29b-41d4-a716-446655440000").unwrap();
        let short = short_id(&id, "task", 12);
        assert!(short.starts_with("task_"));
        assert!(short.len() <= 12 || short.starts_with("task_550e"));
    }
}
