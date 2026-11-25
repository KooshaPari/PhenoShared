# Claude AI Agent Guide — template-lang-zig

This repository is designed to work seamlessly with Claude (and other advanced AI agents) as an autonomous software engineer.

## Quick Start

```bash
# Build
zig build

# Test
zig build test

# Run
zig build run

# Format
zig fmt .
```

## Repository Mental Model

### Project Structure

```
src/
  main.zig           # Entry point
  lib.zig            # Library interface
  domain/
    entities.zig     # Domain types
    errors.zig       # Error sets
  adapters/
    cli.zig          # CLI adapter
    json.zig         # JSON serialization
  application/
    services.zig     # Business logic
build.zig            # Build configuration
```

### build.zig Structure

```zig
const Builder = @import("std").build.Builder;

pub fn build(b: *Builder) void {
    const mode = b.standardReleaseOptions();

    const lib = b.addStaticLibrary("lib", "src/lib.zig");
    lib.setBuildMode(mode);
    lib.installHeader("src/lib.h", "lib.h");

    const tests = b.addTest("src/lib.zig");
    tests.setBuildMode(mode);

    const test_step = b.step("test", "Run tests");
    test_step.dependOn(&tests.step);

    const run = b.addExecutable("app", "src/main.zig");
    run.setBuildMode(mode);
    run.install();

    const run_step = b.step("run", "Run app");
    run_step.dependOn(&run.step);
}
```

### Style Constraints

- **Line length:** 120 characters
- **Formatter:** `zig fmt`
- **No warnings:** Build must be clean
- **Error sets required:** All fallible functions

### Agent Must

- Use Zig idioms (comptime, error sets, defer)
- Explicit memory management
- Document public functions
- Test with std.testing

## Standard Operating Loop

1. **Review** - Read requirements
2. **Research** - Check std library patterns
3. **Plan** - Design types and error sets
4. **Execute** - Implement with TDD
5. **Test** - zig build test
6. **Polish** - zig fmt, clean warnings

## CLI Reference

```bash
# Build modes
zig build
zig build -Drelease-safe
zig build -Drelease-fast
zig build -Drelease-small

# Testing
zig build test
zig test src/lib.zig

# Running
zig build run

# Analysis
zig fmt --check src/
zig build -Dverbose-link

# Cross-compilation
zig build -Dtarget=x86_64-linux-gnu
zig build -Dtarget=aarch64-linux-gnu
```

## Architecture Patterns

### Error Sets

```zig
const DomainError = error{
    NotFound,
    InvalidInput,
    Unauthorized,
    DatabaseError,
};

pub fn findUser(id: u64) DomainError!User {
    const user = try db.query("SELECT * FROM users WHERE id = ?", .{id});
    if (user == null) return DomainError.NotFound;
    return user.?;
}
```

### Memory Arena

```zig
const ArenaAllocator = std.heap.ArenaAllocator;
const GeneralPurposeAllocator = std.heap.GeneralPurposeAllocator;

var gpa = GeneralPurposeAllocator{};
defer std.debug.assert(!gpa.deinit());

var arena = ArenaAllocator.init(gpa.allocator());
defer arena.deinit();
const allocator = arena.allocator();

// Use allocator for all allocations
const user = try allocator.create(User);
```

### Comptime

```zig
fn Matrix(comptime rows: usize, comptime cols: usize, comptime T: type) type {
    return struct {
        data: [rows][cols]T,
        
        fn identity() @This() {
            var result: @This() = undefined;
            inline for (0..rows) |i| {
                inline for (0..cols) |j| {
                    result.data[i][j] = if (i == j) @as(T, 1) else @as(T, 0);
                }
            }
            return result;
        }
    };
}
```

## Testing Patterns

```zig
const expect = std.testing.expect;

test "findUser returns user when exists" {
    const user = try findUser(1);
    try expect(user.id == 1);
    try expect(std.mem.eql(u8, user.name, "Alice"));
}

test "findUser returns error when not found" {
    const result = findUser(999);
    try expect(result == DomainError.NotFound);
}
```

## Security Guidelines

- No null pointers (use optionals)
- Validate all input
- Use bounded allocations
- Sanitize C interop input
- No buffer overflows

## Troubleshooting

```bash
# Memory leaks
zig build -D leak_count

# Valgrind equivalent
zig build -D sanitize-undefined

# Debug builds
zig build -D optimize=Debug
```
