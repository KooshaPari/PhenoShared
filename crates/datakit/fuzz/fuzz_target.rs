#![no_main]

use libfuzzer_sys::fuzz_target;
use datakit::{DataStream, Pipeline};

fuzz_target!(|data: &[i32]| {
    // Build a pipeline that always runs without panicking
    let pipeline = Pipeline::new(Box::new(|x: i32| {
        // Wrap to prevent overflow panics — test that pipeline never panics on valid input
        x.wrapping_mul(2).wrapping_add(1)
    }));

    let input: Vec<DataStream<i32>> = data.iter().copied().map(DataStream::new).collect();
    let output = pipeline.run(input);

    // Invariant: output length always equals input length
    assert_eq!(output.len(), data.len());

    // Invariant: each output element matches the transform
    for (original, transformed) in data.iter().zip(output.iter()) {
        assert_eq!(transformed.data, original.wrapping_mul(2).wrapping_add(1));
    }
});
