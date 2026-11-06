fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_dir = "../../proto";
    println!("cargo:rerun-if-changed={}", proto_dir);

    let protos: Vec<_> = std::fs::read_dir(proto_dir)?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "proto").unwrap_or(false))
        .collect();

    if protos.is_empty() {
        eprintln!("No .proto files found in {}", proto_dir);
        std::process::exit(1);
    }

    prost_build::Config::new()
        .bytes(["."])
        .compile_protos(&protos, &[proto_dir])?;

    Ok(())
}
