//! AgilePlus protobuf messages and gRPC service stubs.
//!
//! Generated at build time from the checked-in protobuf contracts.

pub mod agileplus {
    pub mod v1 {
        tonic::include_proto!("agileplus.v1");
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn generated_contract_namespace_is_available() {
        let _ = crate::agileplus::v1::Feature {
            id: 0,
            slug: String::new(),
            friendly_name: String::new(),
            state: String::new(),
            target_branch: String::new(),
            created_at: String::new(),
            updated_at: String::new(),
            wp_count: 0,
            wp_done: 0,
        };
    }
}
