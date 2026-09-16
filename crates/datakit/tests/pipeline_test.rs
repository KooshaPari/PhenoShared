use datakit::{DataStream, Pipeline};

#[test]
fn test_basic_transform() {
    let pipeline = Pipeline::new(Box::new(|x: i32| x * 2));
    let input = vec![DataStream::new(1), DataStream::new(2), DataStream::new(3)];
    let output = pipeline.run(input);
    assert_eq!(
        output,
        vec![DataStream::new(2), DataStream::new(4), DataStream::new(6)]
    );
}

#[test]
fn test_string_transform() {
    let pipeline = Pipeline::new(Box::new(|x: &str| x.to_uppercase()));
    let input = vec![
        DataStream::new("hello"),
        DataStream::new("world"),
        DataStream::new("rust"),
    ];
    let output = pipeline.run(input);
    assert_eq!(
        output,
        vec![
            DataStream::new(String::from("HELLO")),
            DataStream::new(String::from("WORLD")),
            DataStream::new(String::from("RUST")),
        ]
    );
}

#[test]
fn test_type_conversion() {
    // i32 -> String
    let pipeline = Pipeline::new(Box::new(|x: i32| format!("item_{x}")));
    let input = vec![
        DataStream::new(1),
        DataStream::new(42),
        DataStream::new(999),
    ];
    let output = pipeline.run(input);
    assert_eq!(
        output,
        vec![
            DataStream::new(String::from("item_1")),
            DataStream::new(String::from("item_42")),
            DataStream::new(String::from("item_999")),
        ]
    );
}

#[test]
fn test_large_batch() {
    let pipeline = Pipeline::new(Box::new(|x: i32| x * x));
    let input: Vec<DataStream<i32>> = (0..1000).map(DataStream::new).collect();
    let output = pipeline.run(input);
    assert_eq!(output.len(), 1000);
    for (i, stream) in output.into_iter().enumerate() {
        assert_eq!(stream.data, (i as i32) * (i as i32));
    }
}

#[test]
fn test_single_element() {
    let pipeline = Pipeline::new(Box::new(|x: i32| x + 100));
    let input = vec![DataStream::new(7)];
    let output = pipeline.run(input);
    assert_eq!(output, vec![DataStream::new(107)]);
}
