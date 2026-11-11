#[path = "../src/okf.rs"]
mod okf;

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct Fixture {
    cases: Vec<FixtureCase>,
}

#[derive(serde::Deserialize)]
struct FixtureCase {
    name: String,
    markdown: String,
    valid: bool,
    #[serde(rename = "type")]
    type_name: Option<String>,
    error: Option<String>,
}

#[test]
fn validates_the_versioned_okf_concept_fixture() {
    let fixture: Fixture = serde_json::from_str(include_str!("fixtures/okf/concept_contract.json"))
        .expect("fixture must be valid JSON");

    for case in fixture.cases {
        let result = okf::validate_concept(&case.markdown);
        if case.valid {
            assert_eq!(
                result
                    .expect("valid fixture concept must validate")
                    .type_name,
                case.type_name.expect("valid fixture needs its type"),
                "fixture case: {}",
                case.name
            );
        } else {
            let error = result.expect_err("invalid fixture concept must fail");
            assert!(
                error
                    .to_string()
                    .contains(case.error.as_deref().unwrap_or_default()),
                "fixture case {} returned unexpected error: {error}",
                case.name
            );
        }
    }
}
