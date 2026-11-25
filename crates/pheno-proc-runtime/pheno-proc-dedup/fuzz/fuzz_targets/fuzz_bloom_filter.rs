#![no_main]
use libfuzzer_sys::fuzz_target;
use pheno_proc_dedup::BloomFilter;

fuzz_target!(|data: &[u8]| {
    let mut filter = BloomFilter::new(1024, 3);
    filter.add(data);
    let _ = filter.check(data);
    let _ = filter.check_and_add(data);
});
