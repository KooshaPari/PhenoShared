use anyhow::Result;
use pheno_data_core::{Dataset, Record};
use surreal_bridge::SurrealDataset;

#[tokio::test]
async fn surreal_dataset_records_uses_the_mock_loader() -> Result<()> {
    let dataset = SurrealDataset::new(
        || async {
            Ok(vec![
                Record::new("s1", serde_json::json!({"gene": "BRCA1"})),
                Record::new("s2", serde_json::json!({"gene": "TP53"})),
            ])
        },
        || async { Ok(serde_json::json!({"type": "object"})) },
    );

    let records = dataset.records().await?;

    assert_eq!(records.len(), 2);
    assert_eq!(records[0].fields["gene"], "BRCA1");
    assert_eq!(records[1].fields["gene"], "TP53");
    Ok(())
}

#[tokio::test]
async fn surreal_dataset_schema_returns_the_mock_schema() -> Result<()> {
    let dataset = SurrealDataset::new(
        || async { Ok(vec![Record::new("s1", serde_json::json!({"gene": "EGFR"}))]) },
        || async {
            Ok(serde_json::json!({
                "type": "object",
                "required": ["gene"],
                "properties": {
                    "gene": {"type": "string"}
                }
            }))
        },
    );

    let schema = dataset.schema().await?;

    assert_eq!(schema["type"], "object");
    assert_eq!(schema["required"][0], "gene");
    assert_eq!(schema["properties"]["gene"]["type"], "string");
    Ok(())
}
