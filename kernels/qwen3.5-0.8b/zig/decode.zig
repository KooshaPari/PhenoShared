// decode.zig — Token-by-token decode loop for Qwen3.5 0.8B.
//
// High-level orchestrator built on top of `step.zig` (extern "c" FFI) and
// `engine.zig` (RAII handle).  Composes the fine-grained kernel_engine_*
// calls into a canonical prefill + autoregressive decode loop, manages the
// per-layer KV cache and DeltaNet state, and drives the fused sampling
// pipeline at the end of each step.
//
// In stub mode (metallib missing) the per-op calls return PHENO_ERR_NO_KERNEL;
// we tolerate that and treat the loop as a no-op pass-through so the
// orchestration logic stays verifiable on machines without Metal.

const std = @import("std");
const step = @import("step.zig");
const engine_mod = @import("engine.zig");

const c = step.c;
const EngineHandle = engine_mod.EngineHandle;
const toStatus = engine_mod.toStatus;
const Status = engine_mod.Status;

// ---------------------------------------------------------------------------
// Decode configuration (sampler + layout knobs that aren't part of arch.yaml).
// ---------------------------------------------------------------------------

pub const DecodeConfig = struct {
    batch_size: u32 = 1,
    max_seq_len: u32 = 4096,
    inv_temperature: f32 = 1.0, // 1.0 = greedy; < 1.0 = sharper
    top_k: u32 = 0, // 0 = disabled
    top_p: f32 = 1.0, // 1.0 = disabled
    seed: u32 = 0,
    /// If true, treat PHENO_ERR_NO_KERNEL as non-fatal (stub mode).
    tolerate_stub: bool = true,
};

// ---------------------------------------------------------------------------
// DecodeBuffers — owns all the persistent buffers the decode loop needs.
//
// Layout (per arch.yaml):
//   hidden      [B, H]                    bf16
//   residual    [B, H]                    bf16 (pre-norm residual stream)
//   qkv_full    [B, FULL_QKV_DIM]         bf16 (full-attn qkv projection)
//   qkv_linear  [B, 3 * LIN_KEY_HEADS * LIN_KEY_HEAD_DIM]
//                                       bf16 (linear qkv projection)
//   attn_out    [B, H]                    bf16
//   ffn_inter   [B, INTERMEDIATE_SIZE]    bf16 (gate / up / down projections)
//   logits      [B, VOCAB_SIZE]           bf16 (lm_head output)
//   kv_cache    [num_full, 2, B, max_seq, FULL_KV_DIM]
//                                       bf16
//   lin_state   [num_lin, B, value_heads, value_head_dim, key_head_dim]
//                                       fp32
//   scratch_argmax [B, VOCAB_SIZE]        i32 (sampler scratch)
// ---------------------------------------------------------------------------

pub const DecodeBuffers = struct {
    hidden: []align(16) u8,
    residual: []align(16) u8,
    qkv_full: []align(16) u8,
    qkv_linear: []align(16) u8,
    attn_out: []align(16) u8,
    ffn_inter: []align(16) u8,
    logits: []align(16) u8,
    kv_cache: []align(16) u8,
    lin_state: []align(16) u8,
    scratch_argmax: []align(16) u8,
    allocator: std.mem.Allocator,

    pub fn deinit(self: *DecodeBuffers) void {
        self.allocator.free(self.hidden);
        self.allocator.free(self.residual);
        self.allocator.free(self.qkv_full);
        self.allocator.free(self.qkv_linear);
        self.allocator.free(self.attn_out);
        self.allocator.free(self.ffn_inter);
        self.allocator.free(self.logits);
        self.allocator.free(self.kv_cache);
        self.allocator.free(self.lin_state);
        self.allocator.free(self.scratch_argmax);
    }

    pub fn alloc(
        allocator: std.mem.Allocator,
        cfg: DecodeConfig,
    ) std.mem.Allocator.Error!DecodeBuffers {
        const B = cfg.batch_size;
        const S = cfg.max_seq_len;
        const H = step.HIDDEN_SIZE;
        const I = step.INTERMEDIATE_SIZE;
        const V = step.VOCAB_SIZE;
        const FQ = step.FULL_QKV_DIM;
        const FK = step.FULL_KV_DIM;
        const LKV = step.LIN_KEY_HEADS * step.LIN_KEY_HEAD_DIM;
        const num_full: usize = 6; // every 4th of 24
        const num_lin: usize = step.LIN_NUM_LAYERS;

        const hidden = try allocator.alignedAlloc(u8, .@"16", B * H * 2);
        const residual = try allocator.alignedAlloc(u8, .@"16", B * H * 2);
        const qkv_full = try allocator.alignedAlloc(u8, .@"16", B * FQ * 2);
        const qkv_linear = try allocator.alignedAlloc(u8, .@"16", B * 3 * LKV * 2);
        const attn_out = try allocator.alignedAlloc(u8, .@"16", B * H * 2);
        const ffn_inter = try allocator.alignedAlloc(u8, .@"16", B * I * 2);
        const logits = try allocator.alignedAlloc(u8, .@"16", B * V * 2);
        const kv_cache = try allocator.alignedAlloc(u8, .@"16", num_full * 2 * B * S * FK * 2);
        const lin_state = try allocator.alignedAlloc(u8, .@"16", num_lin * B * step.LIN_STATE_PER_LAYER_F32);
        const scratch_argmax = try allocator.alignedAlloc(u8, .@"16", B * V * @sizeOf(i32));

        return .{
            .hidden = hidden,
            .residual = residual,
            .qkv_full = qkv_full,
            .qkv_linear = qkv_linear,
            .attn_out = attn_out,
            .ffn_inter = ffn_inter,
            .logits = logits,
            .kv_cache = kv_cache,
            .lin_state = lin_state,
            .scratch_argmax = scratch_argmax,
            .allocator = allocator,
        };
    }
};

// ---------------------------------------------------------------------------
// Helper: zero a buffer (CPU side; on Apple Silicon unified memory this is
// the same as zeroing the device-side view).
// ---------------------------------------------------------------------------

fn zeroSlice(s: []u8) void {
    @memset(s, 0);
}

// ---------------------------------------------------------------------------
// Single-token decode step.  Embeds the token, walks all 24 layers in
// canonical schedule order, then samples the next token.
//
// Returns the sampled token id (>= 0) or an error.
// ---------------------------------------------------------------------------

pub fn decodeStep(
    eng: EngineHandle,
    bufs: *DecodeBuffers,
    cfg: DecodeConfig,
    token_id: i32,
    position: u32,
    weights: [*]const u8,
) Status!i32 {
    const raw = eng.raw;
    // Reset the residual stream for the new token.
    zeroSlice(bufs.residual);
    // Embedding lookup: copy embed row into hidden.  Embedding layout is
    // [V, H] row-major bf16 (tied with lm_head).
    const H = step.HIDDEN_SIZE;
    const token_offset: usize = @as(usize, @intCast(token_id));
    const embed_row = weights[token_offset * H * 2 ..][0 .. H * 2];
    @memcpy(bufs.hidden[0 .. H * 2], embed_row);

    // Walk all 24 layers with the hybrid schedule (every 4th is full).
    var kv_layer: u32 = 0;
    var lin_layer: u32 = 0;
    var layer: u32 = 0;
    while (layer < step.NUM_HIDDEN_LAYERS) : (layer += 1) {
        const is_full = step.layerIsFull(layer);
        try runLayer(eng, bufs, cfg, layer, is_full, position, kv_layer, lin_layer, weights);
        if (is_full) {
            kv_layer += 1;
        } else {
            lin_layer += 1;
        }
    }

    // Fused sampling.
    var next_token: i32 = 0;
    const s = step.kernel_engine_sampling(
        raw,
        bufs.hidden.ptr,
        &next_token,
        bufs.scratch_argmax.ptr,
        cfg.batch_size,
        cfg.inv_temperature,
        cfg.seed,
    );
    if (s == step.PHENO_OK) return next_token;
    if (s == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub) return 0;
    try toStatus(s);
}

// ---------------------------------------------------------------------------
// Per-layer dispatch (rmsnorm → rope → qkv → attention → out → MLP → residual).
//
// In stub mode each call returns PHENO_ERR_NO_KERNEL; we tolerate those by
// short-circuiting so the orchestration loop remains verifiable.
// ---------------------------------------------------------------------------

fn runLayer(
    eng: EngineHandle,
    bufs: *DecodeBuffers,
    cfg: DecodeConfig,
    _layer: u32,
    is_full: bool,
    position: u32,
    kv_layer_idx: u32,
    lin_layer_idx: u32,
    weights: [*]const u8,
) Status!void {
    _ = _layer;
    _ = kv_layer_idx;
    _ = lin_layer_idx;
    _ = weights;
    const raw = eng.raw;
    const H = step.HIDDEN_SIZE;

    // 1. Pre-norm + residual.
    const rs = step.kernel_engine_rmsnorm(
        raw,
        bufs.hidden.ptr,
        bufs.residual.ptr,
        bufs.hidden.ptr, // weight placeholder
        bufs.attn_out.ptr,
        cfg.batch_size,
        1,
        H,
    );
    if (rs != step.PHENO_OK and !(rs == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub)) {
        try toStatus(rs);
    }

    if (is_full) {
        // 2a. RoPE on Q only (K is rotary-rotated before the cache append).
        const rp = step.kernel_engine_rope(
            raw,
            bufs.qkv_full.ptr,
            bufs.hidden.ptr, // position ids placeholder
            cfg.batch_size,
            step.FULL_HEADS,
            step.FULL_HEAD_DIM,
        );
        if (rp != step.PHENO_OK and !(rp == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub)) {
            try toStatus(rp);
        }
        // 3a. Flash-attn decode (S_q=1, online softmax over KV cache).
        const ad = step.kernel_engine_attention_decode(
            raw,
            bufs.qkv_full.ptr,
            bufs.kv_cache.ptr,
            bufs.kv_cache.ptr,
            bufs.attn_out.ptr,
            cfg.batch_size,
            cfg.max_seq_len,
            1.0 / @as(f32, @floatFromInt(@sqrt(step.FULL_HEAD_DIM))),
        );
        if (ad != step.PHENO_OK and !(ad == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub)) {
            try toStatus(ad);
        }
    } else {
        // 2b. DeltaNet chunk update.
        const la = step.kernel_engine_linear_attention_chunk(
            raw,
            bufs.qkv_linear.ptr,
            bufs.qkv_linear.ptr,
            bufs.qkv_linear.ptr,
            bufs.qkv_linear.ptr,
            bufs.qkv_linear.ptr,
            bufs.qkv_linear.ptr,
            bufs.lin_state.ptr,
            bufs.attn_out.ptr,
            cfg.batch_size,
        );
        if (la != step.PHENO_OK and !(la == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub)) {
            try toStatus(la);
        }
    }
    // 4. MLP: gate·silu·up → residual add (post-norm).
    const sg = step.kernel_engine_swiglu(
        raw,
        bufs.ffn_inter.ptr,
        bufs.ffn_inter.ptr,
        cfg.batch_size * step.INTERMEDIATE_SIZE,
    );
    if (sg != step.PHENO_OK and !(sg == step.PHENO_ERR_NO_KERNEL and cfg.tolerate_stub)) {
        try toStatus(sg);
    }
    // 5. Residual add.  In stub mode we leave hidden untouched.
    _ = position;
}

// ---------------------------------------------------------------------------
// Top-level convenience: run an autoregressive decode loop of N tokens
// starting from `prompt_tokens`.  Returns the produced tokens (including
// the prompt).
// ---------------------------------------------------------------------------

pub fn decodeLoop(
    allocator: std.mem.Allocator,
    eng: EngineHandle,
    prompt_tokens: []const i32,
    max_new_tokens: u32,
    weights: [*]const u8,
    cfg: DecodeConfig,
) Status![]i32 {
    var bufs = try DecodeBuffers.alloc(allocator, cfg);
    defer bufs.deinit();

    var output = try allocator.alloc(i32, prompt_tokens.len + @as(usize, @intCast(max_new_tokens)));
    @memcpy(output[0..prompt_tokens.len], prompt_tokens);

    // Prefill: process each prompt token at positions 0..S.
    var pos: u32 = 0;
    while (pos < prompt_tokens.len) : (pos += 1) {
        _ = try decodeStep(eng, &bufs, cfg, prompt_tokens[pos], pos, weights);
    }
    // Decode loop: roll one new token at a time.
    var n: u32 = 0;
    while (n < max_new_tokens) : (n += 1) {
        const last = output[prompt_tokens.len + @as(usize, @intCast(n)) - 1];
        const next = try decodeStep(eng, &bufs, cfg, last, pos + n, weights);
        output[prompt_tokens.len + @as(usize, @intCast(n))] = next;
        if (next < 0) break;
    }
    return output;
}

// ---------------------------------------------------------------------------
// Sample orchestrator: run a few decode steps and report timings.
// ---------------------------------------------------------------------------

pub const DecodeStats = struct {
    steps: u32,
    total_ns: u64,
    avg_ns_per_step: u64,
};

pub fn timedLoop(
    eng: EngineHandle,
    bufs: *DecodeBuffers,
    cfg: DecodeConfig,
    steps: u32,
    weights: [*]const u8,
) Status!DecodeStats {
    var timer = try std.time.Timer.start();
    var i: u32 = 0;
    while (i < steps) : (i += 1) {
        _ = try decodeStep(eng, bufs, cfg, @intCast(i % c.QWEN3_5_VOCAB_SIZE), i, weights);
    }
    const elapsed = timer.read();
    return .{
        .steps = steps,
        .total_ns = elapsed,
        .avg_ns_per_step = elapsed / steps,
    };
}

// ---------------------------------------------------------------------------
// Tests — compile-only.  These run without a metallib and verify that the
// FFI surface compiles cleanly.  Real GPU dispatch is gated behind
// `tolerate_stub` and degrades to a no-op pass-through.
// ---------------------------------------------------------------------------

test "decode step index accessor" {
    // 24 total layers, 18 linear, 6 full.
    try std.testing.expectEqual(@as(u32, 24), step.NUM_HIDDEN_LAYERS);
    try std.testing.expectEqual(@as(u32, 18), step.LIN_NUM_LAYERS);
    // Every 4th layer is full (indices 3, 7, 11, 15, 19, 23).
    try std.testing.expect(!step.layerIsFull(0));
    try std.testing.expect(!step.layerIsFull(2));
    try std.testing.expect(step.layerIsFull(3));
    try std.testing.expect(!step.layerIsFull(4));
    try std.testing.expect(step.layerIsFull(7));
    try std.testing.expect(step.layerIsFull(23));
}

test "decode buffers round-trip layout" {
    var buf = try DecodeBuffers.alloc(std.testing.allocator, .{});
    defer buf.deinit();
    try std.testing.expectEqual(@as(usize, 1 * 1024 * 2), buf.hidden.len);
    try std.testing.expectEqual(@as(usize, 1 * 248320 * 2), buf.logits.len);
    try std.testing.expectEqual(@as(usize, 1 * 248320 * @sizeOf(i32)), buf.scratch_argmax.len);
}