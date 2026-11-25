#![no_main]
use libfuzzer_sys::fuzz_target;
use pheno_proc_dedup::DedupFilter;

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let mut filter = DedupFilter::new();
        let _ = filter.check_and_insert(s.to_string());
        let _ = filter.len();
    }
});
