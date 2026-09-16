// bench.zig — Decode throughput / latency benchmark for the Qwen3.5 0.8B
// Metal kernel engine.  Drives the orchestrator in decode.zig for varying
// (batch_size, seq_len) combinations and reports tokens/sec + step latency.
//
// Usage:
//   ./bench                # default sweep: B={1,4,16}, S={64,512,2048}
//   ./bench --steps=100    # 100 decode steps per measurement
//   ./bench --warmup=10    # 10-step warmup before measurement
//
// The bench is designed to be useful both in stub mode (no metallib) and
// in real-GPU mode: in stub mode it measures orchestration overhead, in
// real mode it measures the end-to-end decode loop including per-kernel
// dispatch latency.

const std = @import("std");
const step = @import("step.zig");
const engine_mod = @import("engine.zig");
const decode = @import("decode.zig");

const c = step.c;
const EngineHandle = engine_mod.EngineHandle;

// ---------------------------------------------------------------------------
// CLI parsing — minimal, no flag library.
// ---------------------------------------------------------------------------

const Args = struct {
    steps: u32 = 64,
    warmup: u32 = 4,
    batch_sizes: [3]u32 = .{ 1, 4, 16 },
    seq_lens: [3]u32 = .{ 64, 512, 2048 },
    show_help: bool = false,
};

fn parseArgs(allocator: std.mem.Allocator) !Args {
    var args = Args{};
    var iter = try std.process.argsWithAllocator(allocator);
    defer iter.deinit();
    _ = iter.next(); // skip executable
    while (iter.next()) |arg| {
        if (std.mem.startsWith(u8, arg, "--steps=")) {
            args.steps = try std.fmt.parseInt(u32, arg["--steps=".len..], 10);
        } else if (std.mem.startsWith(u8, arg, "--warmup=")) {
            args.warmup = try std.fmt.parseInt(u32, arg["--warmup=".len..], 10);
        } else if (std.mem.eql(u8, arg, "--help") or std.mem.eql(u8, arg, "-h")) {
            args.show_help = true;
        }
    }
    return args;
}

fn printHelp() void {
    const stdout = std.fs.File.stdout();
    const w = stdout.writer();
    w.writeAll(
        \\bench — Qwen3.5 0.8B decode loop benchmark
        \\
        \\Usage: bench [--steps=N] [--warmup=N] [--help]
        \\
        \\Options:
        \\  --steps=N      Number of decode steps per measurement (default: 64)
        \\  --warmup=N     Number of warmup steps before measurement (default: 4)
        \\  --help, -h     Show this help
        \\
        \\Environment:
        \\  PHENO_METAL_LIB   Path to the .metallib (optional; engine uses stub if missing)
        \\
    ) catch {};
}

// ---------------------------------------------------------------------------
// Synthetic weight blob.  We don't need real weights to exercise the
// orchestration loop; the C++ side will return PHENO_ERR_NO_KERNEL for the
// per-op calls in stub mode, which the decoder tolerates.
// ---------------------------------------------------------------------------

fn allocWeights(allocator: std.mem.Allocator, batch: u32, seq: u32) ![]align(16) u8 {
    // Embedding + per-layer weights + final norm.  Sized generously so any
    // pointer arithmetic in the orchestrator stays in-range.
    const bytes: usize = c.QWEN3_5_VOCAB_SIZE * c.QWEN3_5_HIDDEN_SIZE * 2 +
        c.QWEN3_5_NUM_HIDDEN_LAYERS * c.QWEN3_5_HIDDEN_SIZE * (3 * c.QWEN3_5_HIDDEN_SIZE +
            2 * c.QWEN3_5_INTERMEDIATE_SIZE) * 2 +
        c.QWEN3_5_HIDDEN_SIZE * 2 +
        @as(usize, batch) * seq * 4096;
    const buf = try allocator.alignedAlloc(u8, .@"16", bytes);
    @memset(buf, 0);
    return buf;
}

// ---------------------------------------------------------------------------
// Benchmark a single (batch_size, seq_len) configuration.
// ---------------------------------------------------------------------------

fn benchConfig(
    allocator: std.mem.Allocator,
    eng: EngineHandle,
    batch: u32,
    seq: u32,
    steps: u32,
    warmup: u32,
    weights: [*]const u8,
) !decode.DecodeStats {
    var cfg = decode.DecodeConfig{
        .batch_size = batch,
        .max_seq_len = seq,
    };

    var bufs = try decode.DecodeBuffers.alloc(allocator, cfg);
    defer bufs.deinit();

    // Warmup
    var w: u32 = 0;
    while (w < warmup) : (w += 1) {
        _ = try decode.decodeStep(eng, &bufs, cfg, @intCast(w % c.QWEN3_5_VOCAB_SIZE), w, weights);
    }

    // Timed loop
    return try decode.timedLoop(eng, &bufs, cfg, steps, weights);
}

// ---------------------------------------------------------------------------
// Pretty-print the result table.
// ---------------------------------------------------------------------------

fn printRow(comptime label: []const u8, batch: u32, seq: u32, stats: decode.DecodeStats) void {
    const stdout = std.fs.File.stdout();
    const w = stdout.writer();
    const avg_us = @as(f64, @floatFromInt(stats.avg_ns_per_step)) / 1000.0;
    const tok_per_sec = if (stats.avg_ns_per_step == 0)
        @as(f64, 0.0)
    else
        @as(f64, @floatFromInt(stats.steps)) * 1_000_000_000.0 /
            @as(f64, @floatFromInt(stats.total_ns));
    w.print("{s:<14} B={d:>3} S={d:>5}  steps={d:>4}  avg={d:>8.1} µs/step  {d:>7.1} tok/s\n", .{
        label, batch, seq, stats.steps, avg_us, tok_per_sec,
    }) catch {};
}

fn printHeader() void {
    const stdout = std.fs.File.stdout();
    const w = stdout.writer();
    w.writeAll(
        \\
        \\Qwen3.5 0.8B decode benchmark
        \\================================
        \\
    ) catch {};
    w.writeAll("config          batch   seq_len  steps      avg/step        throughput\n") catch {};
    w.writeAll("----------------------------------------------------------------------\n") catch {};
}

// ---------------------------------------------------------------------------
// Main entry point.
// ---------------------------------------------------------------------------

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = parseArgs(allocator) catch Args{};
    if (args.show_help) {
        printHelp();
        return;
    }

    printHeader();

    // Construct the engine.  In real-GPU mode this picks up the metallib;
    // in stub mode the C++ side logs a warning and returns OK.
    const eng = EngineHandle.create() catch |err| {
        std.debug.print("engine create failed: {s}\n", .{@errorName(err)});
        return err;
    };
    defer eng.destroy();

    const stdout = std.fs.File.stdout();
    stdout.writer().print("device: {s}\n", .{eng.deviceName() catch "unknown"}) catch {};

    // Allocate a generic weight blob.  The orchestrator tolerates stub mode
    // so we don't need real weights for timing the orchestration path.
    const weights = try allocWeights(allocator, args.batch_sizes[0], args.seq_lens[0]);
    defer allocator.free(weights);

    var bi: usize = 0;
    while (bi < args.batch_sizes.len) : (bi += 1) {
        const batch = args.batch_sizes[bi];
        var si: usize = 0;
        while (si < args.seq_lens.len) : (si += 1) {
            const seq = args.seq_lens[si];
            const stats = benchConfig(allocator, eng, batch, seq, args.steps, args.warmup, weights.ptr) catch |err| {
                std.debug.print("[bench B={d} S={d}] failed: {s}\n", .{ batch, seq, @errorName(err) });
                continue;
            };
            printRow("decode", batch, seq, stats);
        }
    }
}