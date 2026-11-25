#![no_main]
use libfuzzer_sys::fuzz_target;
use pheno_proc_queue::*;

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let queue = InMemoryQueueAdapter::new();
        let item = queue.enqueue(s.to_string(), Priority::Normal, None);
        assert!(!item.id.is_empty());
        let _ = queue.dequeue();
    }
});
