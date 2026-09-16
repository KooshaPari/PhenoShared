// tiny_test.metal — minimal kernel to test dispatch path
#include <metal_stdlib>
using namespace metal;

kernel void write_ones(device half* out [[buffer(0)]],
                      uint tgid [[threadgroup_position_in_grid]],
                      uint tid  [[thread_index_in_threadgroup]]) {
    if (tgid == 0 && tid < 1024) {
        out[tid] = half(1.0);
    }
}