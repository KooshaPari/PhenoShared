// tests/test_kernels.zig — Compile-only smoke tests for the Qwen3.5 0.8B
// kernel engine FFI surface.
//
// These tests verify that the FFI bindings in step.zig compile cleanly and
// that the function-pointer ABI matches the C header.  They do NOT require
// a metallib — the per-op dispatch paths tolerate PHENO_ERR_NO_KERNEL.
//
// Run with: `zig build test` from the kernels/qwen3.5-0.8b/zig directory.

const std = @import("std");
const testing = std.testing;
const step = @import("step.zig");
const engine_mod = @import("engine.zig");
const decode = @import("decode.zig");

const c = step.c;
const EngineHandle = engine_mod.EngineHandle;

// ---------------------------------------------------------------------------
// Architecture constants — verify the C header values are reachable from
// Zig via @cImport.  These tests fail loudly if arch.yaml / qwen3_5.h drift.
// ---------------------------------------------------------------------------

test "arch constants match arch.yaml" {
    try testing.expectEqual(@as(i32, 248320), c.QWEN3_5_VOCAB_SIZE);
    try testing.expectEqual(@as(i32, 1024), c.QWEN3_5_HIDDEN_SIZE);
    try testing.expectEqual(@as(i32, 3584), c.QWEN3_5_INTERMEDIATE_SIZE);
    try testing.expectEqual(@as(i32, 24), c.QWEN3_5_NUM_HIDDEN_LAYERS);
    try testing.expectEqual(@as(i32, 262144), c.QWEN3_5_MAX_POSITION_EMB);
    try testing.expectEqual(@as(i32, 8), c.QWEN3_5_FULL_HEADS);
    try testing.expectEqual(@as(i32, 2), c.QWEN3_5_FULL_KV_HEADS);
    try testing.expectEqual(@as(i32, 256), c.QWEN3_5_FULL_HEAD_DIM);
    try testing.expectEqual(@as(i32, 3072), c.QWEN3_5_FULL_QKV_DIM);
    try testing.expectEqual(@as(i32, 32), c.QWEN3_5_ROT_DIM);
    try testing.expectEqual(@as(i32, 16), c.QWEN3_5_LIN_KEY_HEADS);
    try testing.expectEqual(@as(i32, 128), c.QWEN3_5_LIN_KEY_HEAD_DIM);
    try testing.expectEqual(@as(i32, 128), c.QWEN3_5_LIN_VALUE_HEAD_DIM);
    try testing.expectEqual(@as(i32, 4), c.QWEN3_5_LIN_CONV_KERNEL);
    try testing.expectEqual(@as(i32, 18), c.QWEN3_5_LIN_NUM_LAYERS);
}

// ---------------------------------------------------------------------------
// Layer schedule accessor — every 4th layer is full.
// ---------------------------------------------------------------------------

test "layer schedule — 24 layers, every 4th is full" {
    var full_count: u32 = 0;
    var lin_count: u32 = 0;
    for (0..c.QWEN3_5_NUM_HIDDEN_LAYERS) |i| {
        if (step.layerIsFull(@intCast(i))) {
            full_count += 1;
        } else {
            lin_count += 1;
        }
    }
    try testing.expectEqual(@as(u32, 6), full_count);
    try testing.expectEqual(@as(u32, 18), lin_count);
}

// ---------------------------------------------------------------------------
// Status code aliases match the C enum values.
// ---------------------------------------------------------------------------

test "status codes match C enum" {
    try testing.expectEqual(@as(u32, 0), step.PHENO_OK);
    try testing.expectEqual(@as(u32, 1), step.PHENO_ERR_INVALID_ARG);
    try testing.expectEqual(@as(u32, 2), step.PHENO_ERR_NO_DEVICE);
    try testing.expectEqual(@as(u32, 3), step.PHENO_ERR_NO_LIBRARY);
    try testing.expectEqual(@as(u32, 4), step.PHENO_ERR_NO_KERNEL);
    try testing.expectEqual(@as(u32, 5), step.PHENO_ERR_NO_MEMORY);
    try testing.expectEqual(@as(u32, 6), step.PHENO_ERR_ENCODE);
    try testing.expectEqual(@as(u32, 7), step.PHENO_ERR_COMMIT);
    try testing.expectEqual(@as(u32, 8), step.PHENO_ERR_WAIT);
    try testing.expectEqual(@as(u32, 99), step.PHENO_ERR_INTERNAL);
}

// ---------------------------------------------------------------------------
// FFI symbol reachability — just compile-check the extern decls.
// If any of these symbols is missing or has the wrong signature, the test
// file fails to compile, which is exactly what we want.
// ---------------------------------------------------------------------------

test "FFI symbols are reachable from Zig" {
    comptime {
        // Lifecycle
        _ = step.pheno_engine_create;
        _ = step.pheno_engine_destroy;
        _ = step.pheno_engine_load_metallib;
        _ = step.pheno_engine_scratch_sizes;
        _ = step.pheno_engine_alloc;
        _ = step.pheno_engine_has_metal;
        _ = step.pheno_engine_device_name;
        _ = step.pheno_engine_strerror;

        // High-level C++ aliases
        _ = step.qwen3_5_engine_create;
        _ = step.qwen3_5_engine_destroy;
        _ = step.qwen3_5_engine_forward;
        _ = step.qwen3_5_engine_decode_step;

        // Per-op dispatch
        _ = step.kernel_engine_rmsnorm;
        _ = step.kernel_engine_rope;
        _ = step.kernel_engine_swiglu;
        _ = step.kernel_engine_attention_decode;
        _ = step.kernel_engine_attention_prefill;
        _ = step.kernel_engine_linear_attention_chunk;
        _ = step.kernel_engine_sampling;
        _ = step.kernel_engine_tgemv;
    }
}

// ---------------------------------------------------------------------------
// FFI signature spot-checks — verify the parameter types match the C ABI.
// These use @TypeOf at comptime; if the ABI drifts the test fails to compile.
// ---------------------------------------------------------------------------

test "pheno_engine_create ABI" {
    comptime {
        const T = @TypeOf(step.pheno_engine_create);
        try testing.expectEqual(@as(usize, 1), @typeInfo(T).@"fn".params.len);
    }
}

test "kernel_engine_rmsnorm ABI" {
    comptime {
        const T = @TypeOf(step.kernel_engine_rmsnorm);
        // (engine, x, residual, weight, out, B, S, H) -> status
        try testing.expectEqual(@as(usize, 8), @typeInfo(T).@"fn".params.len);
    }
}

test "kernel_engine_sampling ABI" {
    comptime {
        const T = @TypeOf(step.kernel_engine_sampling);
        // (engine, logits, out_token, scratch_argmax, B, inv_T, seed) -> status
        try testing.expectEqual(@as(usize, 7), @typeInfo(T).@"fn".params.len);
    }
}

test "kernel_engine_attention_decode ABI" {
    comptime {
        const T = @TypeOf(step.kernel_engine_attention_decode);
        // (engine, Q, K, V, O, B, S_k, scale) -> status
        try testing.expectEqual(@as(usize, 8), @typeInfo(T).@"fn".params.len);
    }
}

test "qwen3_5_engine_decode_step ABI" {
    comptime {
        const T = @TypeOf(step.qwen3_5_engine_decode_step);
        // (engine, token_id, position, hidden, weights, kv, lin_state, scratch,
        //  scratch_argmax, batch_size, inv_T, seed, out_token) -> status
        try testing.expectEqual(@as(usize, 13), @typeInfo(T).@"fn".params.len);
    }
}

// ---------------------------------------------------------------------------
// Engine creation smoke test — works in both stub mode and real-GPU mode.
// On machines without a Metal device this test will fail with NoDevice.
// ---------------------------------------------------------------------------

test "engine create + destroy (real or stub)" {
    const eng = EngineHandle.create() catch |err| switch (err) {
        error.NoDevice => {
            std.debug.print("[skip] no Metal device available\n", .{});
            return;
        },
        else => return err,
    };
    defer eng.destroy();
    const name_ptr = eng.deviceName() catch "unknown";
    const name = std.mem.span(name_ptr);
    try testing.expect(name.len > 0);
}

test "scratch sizes match arch" {
    const eng = EngineHandle.create() catch |err| switch (err) {
        error.NoDevice => return,
        else => return err,
    };
    defer eng.destroy();

    const s = try eng.scratchSizes(1, 4096);
    try testing.expectEqual(@as(usize, 1 * 4096 * 1024 * 2), s.hidden_bytes);
    try testing.expectEqual(@as(usize, 1 * 248320 * 2), s.logits_bytes);
}

// ---------------------------------------------------------------------------
// Decode buffer layout — verifies the buffers match the architecture dims.
// ---------------------------------------------------------------------------

test "decode buffers sized correctly" {
    var buf = try decode.DecodeBuffers.alloc(testing.allocator, .{});
    defer buf.deinit();
    // B=1, H=1024, bf16 -> 2048 bytes
    try testing.expectEqual(@as(usize, 2048), buf.hidden.len);
    try testing.expectEqual(@as(usize, 2048), buf.residual.len);
    // B=1, V=248320, bf16 -> 496,640 bytes
    try testing.expectEqual(@as(usize, 496_640), buf.logits.len);
    // Sampler scratch: B=1, V=248320, i32 -> 993,280 bytes
    try testing.expectEqual(@as(usize, 248_320 * 4), buf.scratch_argmax.len);
}