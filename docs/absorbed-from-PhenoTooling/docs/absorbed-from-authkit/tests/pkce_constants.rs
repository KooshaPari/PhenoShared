use authkit_core::domain::pkce::VERIFIER_MIN_LEN;

#[test]
fn verifier_min_len_is_43() {
    assert_eq!(VERIFIER_MIN_LEN, 43);
}
