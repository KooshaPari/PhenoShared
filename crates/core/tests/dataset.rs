use anyhow::Result;
use pheno_data_core::{Dataset, DatasetFuture, Record};

struct StubDataset;

impl Dataset for StubDataset {
    fn records(&self) -> DatasetFuture<Vec<Record>> {
        Box::pin(async {
            Ok(vec![Record::new(
                "stub-1",
                serde_json::json!({"kind": "stub"}),
            )])
        })
    }

    fn schema(&self) -> DatasetFuture<serde_json::Value> {
        Box::pin(async {
            Ok(serde_json::json!({
                "type": "object",
                "properties": {
                    "kind": {"type": "string"}
                }
            }))
        })
    }
}

#[tokio::test]
async fn stub_dataset_implements_trait_and_returns_records() -> Result<()> {
    let dataset = StubDataset;
    let records = dataset.records().await?;

    assert_eq!(records.len(), 1);
    assert_eq!(records[0].id, "stub-1");
    assert_eq!(records[0].fields["kind"], "stub");
    Ok(())
}

#[test]
fn record_round_trips_through_serde_json() -> Result<()> {
    let record = Record::new(
        "row-7",
        serde_json::json!({
            "name": "alpha",
            "value": 42,
            "tags": ["core", "serde"]
        }),
    );

    let encoded = serde_json::to_string(&record)?;
    let decoded: Record = serde_json::from_str(&encoded)?;

    assert_eq!(decoded, record);
    Ok(())
}
