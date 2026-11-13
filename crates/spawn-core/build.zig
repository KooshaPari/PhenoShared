const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // --- Static library consumed by Rust via build.rs / extern "C" ---
    const lib_module = b.createModule(.{
        .root_source_file = b.path("src/spawn_core.zig"),
        .target = target,
        .optimize = optimize,
    });
    lib_module.link_libc = true;
    // Keep stack probes out of the .a so consumers do not need Zig compiler-rt
    // when we skip bundling it (Darwin path uses build-obj from build.rs).
    lib_module.stack_check = false;

    const lib = b.addLibrary(.{
        .name = "spawn_core",
        .root_module = lib_module,
        .linkage = .static,
    });
    // NOTE: do NOT call `lib.linkLibC()` here.
    // `Compile.linkLibC()` was deprecated in zig 0.15 ("use
    // `compile.root_module.link_libc = true` instead") and REMOVED in zig
    // 0.16, where it aborts the whole build script with
    // "no field or member function named 'linkLibC' in 'Build.Step.Compile'".
    // `lib_module.link_libc = true` above IS the supported spelling: the
    // deprecated method did nothing but `compile.root_module.link_libc = true`,
    // and `lib.root_module` is `lib_module`. Dropping the call is therefore
    // a no-op on zig 0.13-0.15 and is required on zig 0.16+.
    // Required on Linux so the final rustc link finds __zig_probe_stack from
    // any remaining probe sites. On macOS, `zig build` of this static lib
    // fails resolving libSystem — build.rs uses `zig build-obj` + `ar` instead.
    if (target.result.os.tag != .macos) {
        lib.bundle_compiler_rt = true;
    }
    b.installArtifact(lib);

    // --- Test step: `zig build test` ---
    const test_module = b.createModule(.{
        .root_source_file = b.path("src/spawn_core.zig"),
        .target = target,
        .optimize = optimize,
    });
    test_module.link_libc = true;
    test_module.stack_check = false;

    const unit_tests = b.addTest(.{
        .root_module = test_module,
    });
    // Same reason as above: `test_module.link_libc = true` already does what
    // the removed `unit_tests.linkLibC()` did (`unit_tests.root_module` is
    // `test_module`).
    const run_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run spawn-core unit tests");
    test_step.dependOn(&run_tests.step);
}
