use anyhow::Result;
use std::collections::HashSet;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

fn main() -> Result<()> {
    let root =
        Path::new("/Users/kooshapari/CodeProjects/Phenotype/repos/FocalPoint/apps/ios/FocalPoint");

    let privacy_manifest = root.join("Resources/PrivacyInfo.xcprivacy");
    let info_plist = root.join("Sources/FocalPointApp/Info.plist");
    let sources_dir = root.join("Sources");

    println!("=== Privacy Manifest Audit ===\n");

    // Parse manifests
    let declared_apis = parse_privacy_manifest(&privacy_manifest)?;
    let _declared_usages = parse_info_plist(&info_plist)?;

    println!("Declared Privacy APIs:");
    for api in &declared_apis {
        println!("  - {}", api);
    }
    println!();

    // Scan Swift source for actual framework usage
    let actual_imports = scan_framework_imports(&sources_dir)?;

    println!("Detected Framework Imports:");
    for imp in &actual_imports {
        println!("  - {}", imp);
    }
    println!();

    // Cross-check: warn if declared but unused
    let api_mappings = get_api_mappings();
    let mut unused = Vec::new();

    for api in &declared_apis {
        if let Some(frameworks) = api_mappings.get(api.as_str()) {
            let mut found = false;
            for fw in frameworks {
                if actual_imports.contains(*fw) {
                    found = true;
                    break;
                }
            }
            if !found {
                unused.push(api.clone());
            }
        }
    }

    if !unused.is_empty() {
        println!("⚠️  WARNING: Declared but unused APIs:");
        for api in &unused {
            println!("  - {} (remove from PrivacyInfo.xcprivacy)", api);
        }
        println!();
    }

    // Check for undeclared but used frameworks
    let required_api_mapping = invert_api_mappings();
    let mut undeclared = Vec::new();

    for import in &actual_imports {
        if let Some(apis) = required_api_mapping.get(import.as_str()) {
            for api in apis {
                if !declared_apis.contains(api) {
                    undeclared.push(format!("{} (requires {})", import, api));
                }
            }
        }
    }

    if !undeclared.is_empty() {
        println!("❌ ERROR: Used but undeclared APIs:");
        for item in &undeclared {
            println!("  - {}", item);
        }
        return Err(anyhow::anyhow!("Undeclared privacy APIs detected"));
    }

    println!("✅ Privacy manifest is consistent with Swift source");
    Ok(())
}

fn parse_privacy_manifest(path: &Path) -> Result<HashSet<String>> {
    let content = fs::read(path)?;
    let plist = plist::from_bytes(&content)?;

    let mut apis = HashSet::new();
    if let plist::Value::Dictionary(dict) = plist {
        // Try both key names for compatibility
        let api_array_key = if dict.contains_key("NSPrivacyAccessedAPIs") {
            "NSPrivacyAccessedAPIs"
        } else {
            "NSPrivacyAccessedAPITypes"
        };

        if let Some(plist::Value::Array(api_array)) = dict.get(api_array_key) {
            for api_entry in api_array {
                if let plist::Value::Dictionary(api_dict) = api_entry {
                    if let Some(plist::Value::String(api_type)) =
                        api_dict.get("NSPrivacyAccessedAPIType")
                    {
                        apis.insert(api_type.clone());
                    }
                }
            }
        }
    }

    Ok(apis)
}

fn parse_info_plist(path: &Path) -> Result<HashSet<String>> {
    let content = fs::read(path)?;
    let plist = plist::from_bytes(&content)?;

    let mut usages = HashSet::new();
    if let plist::Value::Dictionary(dict) = plist {
        for (key, _) in dict.iter() {
            if key.contains("UsageDescription") {
                usages.insert(key.clone());
            }
        }
    }

    Ok(usages)
}

fn scan_framework_imports(sources_dir: &Path) -> Result<HashSet<String>> {
    let mut imports = HashSet::new();

    for entry in WalkDir::new(sources_dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().is_some_and(|ext| ext == "swift"))
    {
        let content = fs::read_to_string(entry.path())?;
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("import ") && !trimmed.starts_with("import Sentry") {
                let import_name = trimmed.strip_prefix("import ").unwrap_or("").trim();
                // Filter framework names (capitalized, not module-level)
                if import_name.chars().next().is_some_and(|c| c.is_uppercase()) {
                    imports.insert(import_name.to_string());
                }
            }
        }
    }

    Ok(imports)
}

fn get_api_mappings() -> std::collections::HashMap<&'static str, Vec<&'static str>> {
    let mut map = std::collections::HashMap::new();
    map.insert("NSPrivacyAccessedAPITypeEventKitApis", vec!["EventKit"]);
    // UserDefaults is a Foundation type, typically not explicitly imported
    map.insert("NSPrivacyAccessedAPITypeUserDefaults", vec!["Foundation"]);
    // FileManager is a Foundation type, typically not explicitly imported
    map.insert(
        "NSPrivacyAccessedAPITypeFileTimestampApis",
        vec!["Foundation"],
    );
    map.insert(
        "NSPrivacyAccessedAPITypeUserNotificationCenter",
        vec!["UserNotifications"],
    );
    map.insert("NSPrivacyAccessedAPITypeHealthKitApis", vec!["HealthKit"]);
    map
}

fn invert_api_mappings() -> std::collections::HashMap<String, Vec<String>> {
    let mut map = std::collections::HashMap::new();
    let api_map = get_api_mappings();

    for (api, frameworks) in api_map {
        for fw in frameworks {
            map.entry(fw.to_string())
                .or_insert_with(Vec::new)
                .push(api.to_string());
        }
    }

    map
}
