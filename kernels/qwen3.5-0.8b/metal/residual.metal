// residual.metal — element-wise residual addition for Qwen3.5 0.8B.

#include "types.metal"

kernel void residual_add(
    device half* x              [[buffer(0)]],
    const device half* residual [[buffer(1)]],
    constant uint& N            [[buffer(2)]],
    uint tid                    [[thread_position_in_grid]]) {
    if (tid >= N) return;
    x[tid] = qw_to_f16(qw_to_f32(x[tid]) + qw_to_f32(residual[tid]));
}
