use anyhow::Result;
use pheno_query::{Backend, load};

#[test]
fn load_dispatches_to_the_correct_backend() -> Result<()> {
    assert_eq!(load("surreal://embedded/pheno")?, Backend::Surreal);
    assert_eq!(load("postgres://localhost/pheno")?, Backend::Postgres);
    assert_eq!(load("postgresql://localhost/pheno")?, Backend::Postgres);
    assert!(load("sqlite:///tmp/pheno").is_err());
    Ok(())
}
