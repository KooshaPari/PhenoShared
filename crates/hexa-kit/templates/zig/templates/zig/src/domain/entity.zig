const std = @import("std");
const errors = @import("errors.zig");
const DomainError = errors.DomainError;

/// Entity status enum
pub const EntityStatus = enum {
    pending,
    active,
    archived,
};

/// Example entity demonstrating hexagonal architecture in Zig
pub const ExampleEntity = struct {
    id: u128,
    name: []const u8,
    description: []const u8,
    status: EntityStatus,
    created_at: i64,
    updated_at: i64,

    pub fn init(
        allocator: std.mem.Allocator,
        id: u128,
        name: []const u8,
        description: []const u8,
    ) !ExampleEntity {
        const name_copy = try allocator.dupe(u8, name);
        const desc_copy = try allocator.dupe(u8, description);

        return .{
            .id = id,
            .name = name_copy,
            .description = desc_copy,
            .status = .pending,
            .created_at = std.time.timestamp(),
            .updated_at = std.time.timestamp(),
        };
    }

    pub fn deinit(self: *ExampleEntity, allocator: std.mem.Allocator) void {
        allocator.free(self.name);
        allocator.free(self.description);
    }

    pub fn activate(self: *ExampleEntity) DomainError!void {
        if (self.status != .pending) {
            return DomainError.InvalidStateTransition;
        }
        self.status = .active;
        self.updated_at = std.time.timestamp();
    }

    pub fn archive(self: *ExampleEntity) DomainError!void {
        if (self.status != .active) {
            return DomainError.InvalidStateTransition;
        }
        self.status = .archived;
        self.updated_at = std.time.timestamp();
    }

    pub fn updateName(self: *ExampleEntity, allocator: std.mem.Allocator, new_name: []const u8) !void {
        if (new_name.len == 0) {
            return DomainError.ValidationError;
        }
        const name_copy = try allocator.dupe(u8, new_name);
        allocator.free(self.name);
        self.name = name_copy;
        self.updated_at = std.time.timestamp();
    }
};
