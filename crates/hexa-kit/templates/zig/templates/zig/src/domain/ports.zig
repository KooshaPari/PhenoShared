const std = @import("std");
const Entity = @import("entity.zig").ExampleEntity;
const DomainError = @import("errors.zig").DomainError;

/// Port for repository operations (outbound port)
/// Implementations provide concrete persistence (in-memory, database, etc.)
pub const RepositoryPort = struct {
    vtable: *const VTable,

    const VTable = struct {
        find_by_id: *const fn (ctx: *anyopaque, id: u128) DomainError!?Entity,
        find_all: *const fn (ctx: *anyopaque, allocator: std.mem.Allocator) DomainError![]Entity,
        save: *const fn (ctx: *anyopaque, entity: Entity) DomainError!void,
        delete: *const fn (ctx: *anyopaque, id: u128) DomainError!void,
    };

    pub fn findById(self: RepositoryPort, id: u128) DomainError!?Entity {
        return self.vtable.find_by_id(self.vtable, id);
    }

    pub fn findAll(self: RepositoryPort, allocator: std.mem.Allocator) DomainError![]Entity {
        return self.vtable.find_all(self.vtable, allocator);
    }

    pub fn save(self: RepositoryPort, entity: Entity) DomainError!void {
        return self.vtable.save(self.vtable, entity);
    }

    pub fn delete(self: RepositoryPort, id: u128) DomainError!void {
        return self.vtable.delete(self.vtable, id);
    }
};

/// Port for service/use case operations (inbound port)
/// Called by adapters (HTTP, CLI) to perform business logic
pub const ServicePort = struct {
    vtable: *const VTable,

    const VTable = struct {
        get_example: *const fn (ctx: *anyopaque, id: u128) DomainError!?Entity,
        list_examples: *const fn (ctx: *anyopaque, allocator: std.mem.Allocator) DomainError![]Entity,
        create_example: *const fn (ctx: *anyopaque, name: []const u8, description: []const u8) DomainError!Entity,
        update_example: *const fn (ctx: *anyopaque, id: u128, name: []const u8) DomainError!?Entity,
        delete_example: *const fn (ctx: *anyopaque, id: u128) DomainError!void,
        activate_example: *const fn (ctx: *anyopaque, id: u128) DomainError!?Entity,
        archive_example: *const fn (ctx: *anyopaque, id: u128) DomainError!?Entity,
    };

    pub fn getExample(self: ServicePort, id: u128) DomainError!?Entity {
        return self.vtable.get_example(self.vtable, id);
    }

    pub fn listExamples(self: ServicePort, allocator: std.mem.Allocator) DomainError![]Entity {
        return self.vtable.list_examples(self.vtable, allocator);
    }

    pub fn createExample(self: ServicePort, name: []const u8, description: []const u8) DomainError!Entity {
        return self.vtable.create_example(self.vtable, name, description);
    }

    pub fn updateExample(self: ServicePort, id: u128, name: []const u8) DomainError!?Entity {
        return self.vtable.update_example(self.vtable, id, name);
    }

    pub fn deleteExample(self: ServicePort, id: u128) DomainError!void {
        return self.vtable.delete_example(self.vtable, id);
    }

    pub fn activateExample(self: ServicePort, id: u128) DomainError!?Entity {
        return self.vtable.activate_example(self.vtable, id);
    }

    pub fn archiveExample(self: ServicePort, id: u128) DomainError!?Entity {
        return self.vtable.archive_example(self.vtable, id);
    }
};
