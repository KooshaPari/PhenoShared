// build.zig — Qwen3.5 0.8B Metal kernel suite build orchestration.
//
// Builds (via sub-steps):
//   1. metal        : Metal kernel library (.metallib) via `make -C metal`.
//   2. cpp          : C++ host library (libpheno_qwen.dylib) from cpp/kernel_engine.mm.
//   3. lib          : Zig static library (libpheno_qwen_zig.a) wrapping the C ABI.
//   4. test         : FFI / arch-constant tests (no GPU calls).
//   5. bench        : decode-loop benchmark executable.
//
// Run from this directory: `zig build`, `zig build test`, `zig build bench`.
// Compat: Zig 0.16.x (Build API rewrite).

const std = @import("std");
const builtin = @import("builtin");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // ----- 1. Metal kernel library (.metallib) ---------------------------
    // Compiles metal/*.metal -> build/kernels.metallib.
    // We invoke the Makefile in metal/ so the same compilation path is used
    // as direct `make -C metal`.  This produces the .metallib consumed by
    // the C++ engine at runtime.
    const metal_step = b.step("metal", "Compile Metal kernels to .metallib");
    const make_metal = b.addSystemCommand(&.{
        "make", "-C", "metal", "BUILD_DIR=../build",
    });
    metal_step.dependOn(&make_metal.step);
    b.getInstallStep().dependOn(metal_step);

    // ----- 2. C++ host library (libpheno_qwen.dylib) ---------------------
    // The Objective-C++ source is the only .mm we have; we don't try to
    // compile a separate cpp/kernel_engine.cpp or kernel_engine_decode.mm
    // because those don't exist (per the scaffolding commit).  The entire
    // engine lives in a single translation unit.
    //
    // Zig 0.16: framework linking moved from Compile step → Module.
    const cpp_module = b.createModule(.{
        .target = target,
        .optimize = optimize,
    });
    cpp_module.linkFramework("Metal", .{});
    cpp_module.linkFramework("Foundation", .{});
    cpp_module.addIncludePath(.{ .cwd_relative = "../include" });
    cpp_module.addCSourceFile(.{
        .file = .{ .cwd_relative = "../cpp/kernel_engine.mm" },
        .flags = &.{
            "-std=c++20",
            "-fobjc-arc",
            "-fno-exceptions",
            "-fno-rtti",
        },
    });
    cpp_module.link_libcpp = true;
    const cpp_lib = b.addLibrary(.{
        .name = "pheno_qwen",
        .linkage = .dynamic,
        .root_module = cpp_module,
    });
    const cpp_step = b.step("cpp", "Build C++ host library (libpheno_qwen.dylib)");
    cpp_step.dependOn(&cpp_lib.step);
    b.getInstallStep().dependOn(cpp_step);

    // ----- 3. Zig static library (libpheno_qwen_zig.a) -------------------
    // Wraps the C ABI in idiomatic Zig types.  Used by host binaries that
    // want zero-cost FFI without a dynamic library boundary.
    const zig_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../zig/engine.zig" },
        .target = target,
        .optimize = optimize,
    });
    zig_module.linkLibrary(cpp_lib);
    zig_module.addIncludePath(.{ .cwd_relative = "../include" });
    const zig_lib = b.addLibrary(.{
        .name = "pheno_qwen_zig",
        .linkage = .static,
        .root_module = zig_module,
    });
    b.installArtifact(zig_lib);

    // ----- 4. Tests -------------------------------------------------------
    // test_kernels.zig (in ../tests/) imports step.zig, engine.zig, decode.zig
    // by short name.  We register them as named modules so @import("step.zig")
    // resolves to ../zig/step.zig.
    const step_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../zig/step.zig" },
        .target = target,
        .optimize = optimize,
    });
    step_module.addIncludePath(.{ .cwd_relative = "../include" });
    const engine_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../zig/engine.zig" },
        .target = target,
        .optimize = optimize,
    });
    engine_module.addImport("step.zig", step_module);
    engine_module.addIncludePath(.{ .cwd_relative = "../include" });
    const decode_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../zig/decode.zig" },
        .target = target,
        .optimize = optimize,
    });
    decode_module.addImport("step.zig", step_module);
    decode_module.addImport("engine.zig", engine_module);
    decode_module.addIncludePath(.{ .cwd_relative = "../include" });

    const test_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../tests/test_kernels.zig" },
        .target = target,
        .optimize = optimize,
    });
    test_module.addImport("step.zig", step_module);
    test_module.addImport("engine.zig", engine_module);
    test_module.addImport("decode.zig", decode_module);
    test_module.addIncludePath(.{ .cwd_relative = "../include" });

    const test_step = b.step("test", "Run kernel FFI / arch-constant tests");
    const tests = b.addTest(.{ .root_module = test_module });
    test_step.dependOn(&tests.step);

    // ----- 5. Bench harness ----------------------------------------------
    const bench_module = b.createModule(.{
        .root_source_file = .{ .cwd_relative = "../zig/bench.zig" },
        .target = target,
        .optimize = .ReleaseFast,
    });
    bench_module.linkLibrary(cpp_lib);
    bench_module.addIncludePath(.{ .cwd_relative = "../include" });
    const bench = b.addExecutable(.{
        .name = "bench",
        .root_module = bench_module,
    });
    b.installArtifact(bench);
    const bench_step = b.step("bench", "Build the decode-loop benchmark binary");
    bench_step.dependOn(&bench.step);

    // ----- 6. Default `zig build` ----------------------------------------
    // Default target: build the cpp_lib, the zig_lib, and the bench binary
    // (skipping the metallib compile because that needs xcrun metal).
    const default_step = b.getInstallStep();
    default_step.dependOn(&bench.step);
}