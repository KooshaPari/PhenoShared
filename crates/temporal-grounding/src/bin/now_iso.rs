use chrono::Utc;

fn main() {
    println!(
        "{}",
        Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
    );
}
