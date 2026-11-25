const std = @import("std");
const Entity = @import("entity.zig").ExampleEntity;
const DomainError = @import("errors.zig").DomainError;
const ports = @import("ports.zig");
const ServicePort = ports.ServicePort;
const RepositoryPort = ports.RepositoryPort;

/// In-memory implementation of the RepositoryPort
pub const InMemoryRepository = struct {
    allocator: std.mem.Allocator,
    data: std.AutoHashMap(u128, Entity),
    mutex: std.Thread.Mutex,

    pub fn init(allocator: std.mem.Allocator) InMemoryRepository {
        return .{
            .allocator = allocator,
            .data = std.AutoHashMap(u128, Entity).init(allocator),
            .mutex = std.Thread.Mutex{},
        };
    }

    pub fn deinit(self: *InMemoryRepository) void {
        var iter = self.data.valueIterator();
        while (iter.next()) |entity| {
            var mut_entity = entity.*;
            mut_entity.deinit(self.allocator);
        }
        self.data.deinit();
    }

    pub fn toPort(self: *InMemoryRepository) RepositoryPort {
        return .{
            .vtable = &.{
                .find_by_id = findByIdImpl,
                .find_all = findAllImpl,
                .save = saveImpl,
                .delete = deleteImpl,
            },
        };
    }

    fn findByIdImpl(ctx: *anyopaque, id: u128) DomainError!?Entity {
        const self = @ptrCast(*InMemoryRepository, @alignCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.data.get(id);
    }

    fn findAllImpl(ctx: *anyopaque, allocator: std.mem.Allocator) DomainError![]Entity {
        const self = @ptrCast(*InMemoryRepository, @alignCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();

        var result = try allocator.alloc(Entity, self.data.count());
        var iter = self.data.valueIterator();
        var i: usize = 0;
        while (iter.next()) |entity| {
            result[i] = entity.*;
            i += 1;
        }
        return result;
    }

    fn saveImpl(ctx: *anyopaque, entity: Entity) DomainError!void {
        const self = @ptrCast(*InMemoryRepository, @alignCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();

        if (self.data.contains(entity.id)) {
            var existing = self.data.getPtr(entity.id).?;
            existing.deinit(self.allocator);
        }
        try self.data.put(entity.id, entity);
    }

    fn deleteImpl(ctx: *anyopaque, id: u128) DomainError!void {
        const self = @ptrCast(*InMemoryRepository, @alignCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();

        if (self.data.fetchRemove(id)) |kv| {
            var entity = kv.value;
            entity.deinit(self.allocator);
        }
    }
};
