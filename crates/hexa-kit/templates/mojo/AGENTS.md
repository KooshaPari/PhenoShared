# Claude AI Agent Guide — template-lang-mojo

This repository is designed to work seamlessly with Claude (and other advanced AI agents) as an autonomous software engineer.

## Quick Start

```bash
# Build
mojo build src/main.mojo

# Run
mojo run src/main.mojo

# Test
mojo test src/

# Format
mojo format src/
```

## Repository Mental Model

### Project Structure

```
src/
  main.mojo           # Entry point
  lib.mojo             # Library interface
  models/
    tensor.mojo       # Tensor operations
  pipelines/
    ml_pipeline.mojo  # ML pipeline
  kernels/
    gpu_kernel.mojo   # GPU kernels
  utils/
    memory.mojo       # Memory utilities
tests/
  test_tensor.mojo
  test_pipeline.mojo
```

### Style Constraints

- **Line length:** 100 characters
- **Formatter:** `mojo format`
- **Prefer structs:** Over classes for performance
- **Use owned values:** For memory efficiency

### Agent Must

- Use Mojo idioms (traits, constraints, SIMD)
- Prefer structs for data structures
- Leverage MAX for ML operations
- Document public functions
- Benchmark performance-critical code

## Standard Operating Loop

1. **Review** - Read requirements
2. **Research** - Check Mojo patterns
3. **Plan** - Design with traits and constraints
4. **Execute** - Implement incrementally
5. **Benchmark** - Measure performance
6. **Polish** - Format and document

## CLI Reference

```bash
# Development
mojo run src/main.mojo
mojo build --opt-level 3 src/main.mojo

# Testing
mojo test src/
mojo test src/ --benchmark

# Analysis
mojo check src/
mojo format --check src/

# Performance
mojo profile src/main.mojo
```

## Architecture Patterns

### Struct with Traits

```mojo
from tensor import Tensor

trait Model[T: AnyType]:
    fn forward(self, input: Tensor[T]) -> Tensor[T]:
        ...

struct Linear(Model[DType.float32]):
    var weight: Tensor[DType.float32]
    var bias: Tensor[DType.float32]

    fn __init__(inout self, in_features: Int, out_features: Int):
        self.weight = Tensor[DType.float32](out_features, in_features)
        self.bias = Tensor[DType.float32](out_features)

    fn forward(self, input: Tensor[DType.float32]) -> Tensor[DType.float32]:
        return matmul(input, self.weight^) + self.bias
```

### SIMD Operations

```mojo
from simd import SIMD

fn vector_add[a: Int](x: SIMD[DType.float32, a], y: SIMD[DType.float32, a]) -> SIMD[DType.float32, a]:
    return x + y

fn add_vectors(out: Tensor[DType.float32], x: Tensor[DType.float32], y: Tensor[DType.float32]):
    alias simd_width = SIMD[DType.float32, 8].width
    for i in range(0, x.num_elements(), simd_width):
        alias simd_end = min(i + simd_width, x.num_elements())
        var xi = x.load[width=simd_width](i)
        var yi = y.load[width=simd_width](i)
        var result = vector_add(xi, yi)
        result.store(width=simd_width, to=out, index=i)
```

### GPU Kernel Pattern

```mojo
from gpu import gpu

@gpu.jit
fn kernel_add(output: Tensor[DType.float32], x: Tensor[DType.float32], y: Tensor[DType.float32], n: Int):
    idx = gpu.thread_index_x()
    if idx < n:
        output[idx] = x[idx] + y[idx]

fn gpu_add(output: Tensor[DType.float32], x: Tensor[DType.float32], y: Tensor[DType.float32]):
    let n = x.num_elements()
    gpu.launch[blocks=1, threads_per_block=256](kernel_add, output, x, y, n)
```

## Testing Patterns

```mojo
from testing import assert_equal

fn test_linear_forward():
    var linear = Linear(2, 3)
    var input = Tensor[DType.float32](1, 2)
    input[0, 0] = 1.0
    input[0, 1] = 2.0

    let output = linear.forward(input)
    assert_equal(output.shape()[0], 1)
    assert_equal(output.shape()[1], 3)

fn main():
    test_linear_forward()
```

## Security Guidelines

- No buffer overflows (Mojo prevents these)
- Validate tensor shapes
- Check index bounds
- Sanitize input data
- Use bound checks in debug mode

## Troubleshooting

```bash
# Build errors
mojo check src/

# Performance issues
mojo profile src/main.mojo --detailed

# Memory issues
mojo build --debug-level full src/main.mojo
```
