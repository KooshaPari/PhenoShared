use std::fs;

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::json;
use tempfile::tempdir;

#[test]
fn get_reads_merged_config() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let base = root.path().join("base.json");
    let overlay = root.path().join("overlay.json");
    fs::write(&base, r#"{"service":{"url":"https://base.example"}}"#)?;
    fs::write(&overlay, r#"{"service":{"url":"https://overlay.example"}}"#)?;

    let assert = Command::cargo_bin("phenoctl")?
        .args([
            "get",
            "service.url",
            "--file",
            base.to_str().unwrap(),
            "--file",
            overlay.to_str().unwrap(),
        ])
        .assert();

    assert
        .success()
        .stdout(predicate::str::contains("https://overlay.example"));
    Ok(())
}

#[test]
fn set_updates_value_and_prints_json() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let base = root.path().join("base.json");
    fs::write(&base, r#"{"service":{"url":"https://base.example"}}"#)?;

    let assert = Command::cargo_bin("phenoctl")?
        .args([
            "set",
            "service.port",
            "8080",
            "--file",
            base.to_str().unwrap(),
        ])
        .assert();

    assert
        .success()
        .stdout(predicate::str::contains("\"service\":"))
        .stdout(predicate::str::contains("8080"));
    Ok(())
}

#[test]
fn validate_schema_pass_and_fail() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let config = root.path().join("config.json");
    let schema = root.path().join("schema.json");
    fs::write(
        &config,
        r#"{"service":{"url":"https://base.example","enabled":true}}"#,
    )?;
    fs::write(
        &schema,
        json!({
            "fields": [
                {"name":"service.url","required":true,"type_hint":"string"},
                {"name":"service.enabled","required":false,"type_hint":"boolean"},
            ]
        })
        .to_string(),
    )?;

    let ok = Command::cargo_bin("phenoctl")?
        .args([
            "validate",
            "--file",
            config.to_str().unwrap(),
            "--schema",
            schema.to_str().unwrap(),
        ])
        .assert();
    ok.success().stdout(predicate::str::contains("valid"));

    fs::write(&config, r#"{"service":{"enabled":true}}"#)?;
    let bad = Command::cargo_bin("phenoctl")?
        .args([
            "validate",
            "--file",
            config.to_str().unwrap(),
            "--schema",
            schema.to_str().unwrap(),
        ])
        .assert();
    bad.failure();
    Ok(())
}

#[test]
fn encrypt_and_decrypt_roundtrip() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let input = root.path().join("plain.json");
    let encrypted = root.path().join("cipher.enc");
    let decrypted = root.path().join("out.json");
    fs::write(&input, r#"{"api":"v1","enabled":true}"#)?;

    let pass = "correct horse battery staple";
    Command::cargo_bin("phenoctl")?
        .args([
            "encrypt",
            input.to_str().unwrap(),
            encrypted.to_str().unwrap(),
            "--passphrase",
            pass,
        ])
        .assert()
        .success();

    Command::cargo_bin("phenoctl")?
        .args([
            "decrypt",
            encrypted.to_str().unwrap(),
            "--passphrase",
            pass,
            "--output",
            decrypted.to_str().unwrap(),
        ])
        .assert()
        .success();

    let decrypted_text = fs::read_to_string(decrypted)?;
    assert!(decrypted_text.contains("\"api\":\"v1\""));
    Ok(())
}

#[test]
fn layers_prints_merge_order() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let first = root.path().join("first.json");
    let second = root.path().join("second.json");
    fs::write(&first, r#"{"a":1}"#)?;
    fs::write(&second, r#"{"a":2}"#)?;

    let assert = Command::cargo_bin("phenoctl")?
        .args([
            "layers",
            "--file",
            first.to_str().unwrap(),
            "--file",
            second.to_str().unwrap(),
        ])
        .assert();

    assert
        .success()
        .stdout(predicate::str::contains("1: name="))
        .stdout(predicate::str::contains("2: name="));
    Ok(())
}

#[test]
fn watch_once_exits_with_initial_payload() -> Result<(), Box<dyn std::error::Error>> {
    let root = tempdir()?;
    let payload = root.path().join("payload.json");
    let encrypted = root.path().join("payload.enc");
    fs::write(&payload, r#"{"ok":true}"#)?;

    let pass = "watch-secret";
    Command::cargo_bin("phenoctl")?
        .args([
            "encrypt",
            payload.to_str().unwrap(),
            encrypted.to_str().unwrap(),
            "--passphrase",
            pass,
        ])
        .assert()
        .success();

    let assert = Command::cargo_bin("phenoctl")?
        .args([
            "watch",
            "--file",
            encrypted.to_str().unwrap(),
            "--passphrase",
            pass,
            "--once",
        ])
        .assert();

    assert
        .success()
        .stdout(predicate::str::contains("\"ok\": true"));
    Ok(())
}
