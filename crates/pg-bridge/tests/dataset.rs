use anyhow::Result;
use pg_bridge::PgDataset;
use pheno_data_core::{Dataset, Record};

#[tokio::test]
async fn pg_dataset_records_uses_the_mock_loader() -> Result<()> {
    let dataset = PgDataset::new(
        || async {
            Ok(vec![
                Record::new("p1", serde_json::json!({"sample": "A"})),
                Record::new("p2", serde_json::json!({"sample": "B"})),
            ])
        },
        || async { Ok(serde_json::json!({"type": "object"})) },
    );

    let records = dataset.records().await?;

    assert_eq!(records.len(), 2);
    assert_eq!(records[0].id, "p1");
    assert_eq!(records[1].fields["sample"], "B");
    Ok(())
}

#[tokio::test]
async fn pg_dataset_schema_returns_the_mock_schema() -> Result<()> {
    let dataset = PgDataset::new(
        || async { Ok(vec![Record::new("p1", serde_json::json!({"sample": "A"}))]) },
        || async {
            Ok(serde_json::json!({
                "type": "object",
                "properties": {
                    "sample": {"type": "string"},
                    "score": {"type": "number"}
                }
            }))
        },
    );

    let schema = dataset.schema().await?;

    assert_eq!(schema["type"], "object");
    assert_eq!(schema["properties"]["sample"]["type"], "string");
    assert_eq!(schema["properties"]["score"]["type"], "number");
    Ok(())
}
