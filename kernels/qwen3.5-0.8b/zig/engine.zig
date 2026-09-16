// engine.zig — Zig binding for the Qwen3.5 0.8B kernel engine.
//
// The C++ library (libpheno_qwen) is the actual implementation.  This file
// provides idiomatic Zig types, error handling, and a high-level model
// forward API.
//
// Build: see ../build.zig.

const std = @import("std");
const c = @cImport({
    @cInclude("kernel_engine.h");
    @cInclude("qwen3_5.h");
});

pub const Status = error{
    InvalidArg,
    NoDevice,
    NoLibrary,
    NoKernel,
    NoMemory,
    Encode,
    Commit,
    Wait,
    Internal,
};

fn toStatus(s: c.pheno_status_t) Status!void {
    return switch (s) {
        c.PHENO_OK => {},
        c.PHENO_ERR_INVALID_ARG => error.InvalidArg,
        c.PHENO_ERR_NO_DEVICE => error.NoDevice,
        c.PHENO_ERR_NO_LIBRARY => error.NoLibrary,
        c.PHENO_ERR_NO_KERNEL => error.NoKernel,
        c.PHENO_ERR_NO_MEMORY => error.NoMemory,
        c.PHENO_ERR_ENCODE => error.Encode,
        c.PHENO_ERR_COMMIT => error.Commit,
        c.PHENO_ERR_WAIT => error.Wait,
        else => error.Internal,
    };
}

// Re-use the cImport'd opaque struct from the C header so the Zig handle
// and the FFI symbols agree on the same opaque pointer type.  This avoids
// the dual-opaque cast error when passing `&raw` to `pheno_engine_create`.
pub const Engine = c.pheno_engine_s;

pub const LayerInfo = struct {
    layer_index: u32,
    is_full_attention: bool,
    conv_kernel_dim: u32,
    num_kv_heads: u32,
    head_dim: u32,
    key_head_dim: u32,
    value_head_dim: u32,
};

pub const ScratchSizes = struct {
    hidden_bytes: usize,
    qkv_full_bytes: usize,
    qkv_linear_bytes: usize,
    attn_out_bytes: usize,
    ffn_inter_bytes: usize,
    logits_bytes: usize,
    state_bytes_per_layer: usize,
    kv_cache_bytes_per_layer: usize,
};

pub const EngineHandle = struct {
    raw: *Engine,

    pub fn create() !EngineHandle {
        var raw: ?*Engine = null;
        try toStatus(c.pheno_engine_create(&raw));
        return .{ .raw = raw orelse unreachable };
    }

    pub fn destroy(self: EngineHandle) void {
        _ = c.pheno_engine_destroy(self.raw);
    }

    pub fn scratchSizes(
        self: EngineHandle,
        batch: u32,
        max_seq: u32,
    ) !ScratchSizes {
        var s: c.pheno_scratch_sizes_t = undefined;
        try toStatus(c.pheno_engine_scratch_sizes(self.raw, batch, max_seq, &s));
        return .{
            .hidden_bytes = s.hidden_bytes,
            .qkv_full_bytes = s.qkv_full_bytes,
            .qkv_linear_bytes = s.qkv_linear_bytes,
            .attn_out_bytes = s.attn_out_bytes,
            .ffn_inter_bytes = s.ffn_inter_bytes,
            .logits_bytes = s.logits_bytes,
            .state_bytes_per_layer = s.state_bytes_per_layer,
            .kv_cache_bytes_per_layer = s.kv_cache_bytes_per_layer,
        };
    }

    pub fn forwardLayer(
        self: EngineHandle,
        layer_index: u32,
        batch: u32,
        seq_len: u32,
        hidden_in: [*]const u8,
        hidden_out: [*]u8,
        layer_weights: [*]const u8,
        scratch: [*]u8,
    ) !void {
        try toStatus(c.pheno_engine_forward_layer(
            self.raw,
            layer_index,
            batch,
            seq_len,
            hidden_in,
            hidden_out,
            layer_weights,
            scratch,
        ));
    }

    pub fn decodeStep(
        self: EngineHandle,
        batch: u32,
        position: u32,
        token_ids: [*]const i32,
        hidden_state_out: [*]u8,
        weights: [*]const u8,
        kv_cache: [*]u8,
        lin_state_cache: [*]u8,
    ) !void {
        try toStatus(c.pheno_engine_decode_step(
            self.raw,
            batch,
            position,
            token_ids,
            hidden_state_out,
            weights,
            kv_cache,
            lin_state_cache,
        ));
    }

    pub fn deviceName(self: EngineHandle) ![*:0]const u8 {
        var name: [*c]const u8 = undefined;
        try toStatus(c.pheno_engine_device_name(self.raw, &name));
        return name;
    }
};

// ----- Convenience: print layer schedule for Qwen3.5 0.8B -----
pub fn printLayerSchedule(writer: anytype) !void {
    try writer.writeAll("Qwen3.5 0.8B layer schedule (24 layers, F = full, L = linear):\n");
    for (0..c.QWEN3_5_NUM_HIDDEN_LAYERS) |i| {
        const full = c.QWEN3_5_LAYER_IS_FULL[i];
        try writer.writeAll(if (full != 0) "F " else "L ");
        if ((i + 1) % 8 == 0) try writer.writeAll("\n");
    }
    try writer.writeAll("\n");
}

test "engine creates and destroys" {
    const eng = try EngineHandle.create();
    defer eng.destroy();

    const sizes = try eng.scratchSizes(1, 4096);
    try std.testing.expect(sizes.hidden_bytes == 1 * 4096 * 1024 * 2);
    try std.testing.expect(sizes.logits_bytes == 1 * 248320 * 2);
}

test "printLayerSchedule smoke" {
    var buf: [512]u8 = undefined;
    var w = std.fs.File.stderr().writer(&buf);
    try printLayerSchedule(&w.interface);
}
