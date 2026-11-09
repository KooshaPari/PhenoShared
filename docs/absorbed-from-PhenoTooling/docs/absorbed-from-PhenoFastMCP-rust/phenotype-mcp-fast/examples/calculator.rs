use phenotype_mcp_fast::{FastMcp, tool};
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::json;

#[derive(JsonSchema, Deserialize)]
struct AddParams {
    a: i32,
    b: i32,
}

#[tool]
fn add(params: AddParams) -> Result<i32, String> {
    Ok(params.a + params.b)
}

#[derive(JsonSchema, Deserialize)]
struct GreetParams {
    name: String,
}

#[tool]
fn greet(params: GreetParams) -> Result<String, String> {
    Ok(format!("Hello, {}!", params.name))
}

#[tokio::main]
async fn main() {
    FastMcp::new("calculator", "1.0.0")
        .with_tool(add__Tool::tool_def(), add__Tool::call)
        .with_tool(greet__Tool::tool_def(), greet__Tool::call)
        .run_stdio()
        .await;
}
