use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Proto files live in this repository's local proto/ directory so standalone clones build.
    let proto_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..") // repo root
        .join("proto");

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(
            &[proto_root.join("agileplus/v1/agents.proto")],
            &[&proto_root],
        )?;

    Ok(())
}
