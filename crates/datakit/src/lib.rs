/// A single data record flowing through a pipeline.
///
/// Wraps a value of type `T` — the core data unit that sources emit,
/// transforms process, and sinks consume.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DataStream<T> {
    pub data: T,
}

impl<T> DataStream<T> {
    pub fn new(data: T) -> Self {
        Self { data }
    }
}

/// Type-safe entrypoint for a data pipeline.
///
/// A pipeline accepts a vector of `DataStream<T>` inputs, applies a
/// transformation, and produces `DataStream<U>` outputs.
///
/// # Example
///
/// ```
/// use datakit::{DataStream, Pipeline};
///
/// let double = Pipeline::new(Box::new(|x: i32| x * 2));
/// let input  = vec![DataStream::new(1), DataStream::new(2)];
/// let output = double.run(input);
/// assert_eq!(output, vec![DataStream::new(2), DataStream::new(4)]);
/// ```
pub struct Pipeline<T, U> {
    transform: Box<dyn Fn(T) -> U>,
}

impl<T, U> Pipeline<T, U> {
    pub fn new(transform: Box<dyn Fn(T) -> U>) -> Self {
        Self { transform }
    }

    /// Run the pipeline over a batch of input streams.
    pub fn run(&self, input: Vec<DataStream<T>>) -> Vec<DataStream<U>> {
        input
            .into_iter()
            .map(|stream| DataStream::new((self.transform)(stream.data)))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_datastream_new() {
        let stream = DataStream::new(42);
        assert_eq!(stream.data, 42);

        let stream_str = DataStream::new(String::from("hello"));
        assert_eq!(stream_str.data, "hello");

        let stream_vec = DataStream::new(vec![1, 2, 3]);
        assert_eq!(stream_vec.data, vec![1, 2, 3]);
    }

    #[test]
    fn test_pipeline_empty_input() {
        let pipeline = Pipeline::new(Box::new(|x: i32| x + 1));
        let input: Vec<DataStream<i32>> = vec![];
        let output = pipeline.run(input);
        assert!(output.is_empty());
    }

    #[test]
    fn test_pipeline_identity_transform() {
        let pipeline = Pipeline::new(Box::new(|x: i32| x));
        let input = vec![DataStream::new(10), DataStream::new(20), DataStream::new(30)];
        let output = pipeline.run(input);
        assert_eq!(output, vec![DataStream::new(10), DataStream::new(20), DataStream::new(30)]);
    }

    #[test]
    fn test_pipeline_composition() {
        // Chain two transforms: double then add one
        let double = Pipeline::new(Box::new(|x: i32| x * 2));
        let add_one = Pipeline::new(Box::new(|x: i32| x + 1));

        let input = vec![DataStream::new(1), DataStream::new(2), DataStream::new(3)];
        let doubled = double.run(input);
        let result = add_one.run(doubled);

        // (1*2)+1=3, (2*2)+1=5, (3*2)+1=7
        assert_eq!(result, vec![DataStream::new(3), DataStream::new(5), DataStream::new(7)]);
    }
}
