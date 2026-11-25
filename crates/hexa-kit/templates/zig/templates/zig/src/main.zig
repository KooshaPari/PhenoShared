const std = @import("std");

// Domain ports - using context pointer pattern for Zig 0.15
pub const RepositoryPort = struct {
    context: *anyopaque,
    vtable: *const VTable,
    
    pub const VTable = struct {
        findById: *const fn (*anyopaque, u128) anyerror!?ExampleEntity,
        findAll: *const fn (*anyopaque, std.mem.Allocator) anyerror![]ExampleEntity,
        save: *const fn (*anyopaque, ExampleEntity) anyerror!void,
        delete: *const fn (*anyopaque, u128) anyerror!void,
    };
    
    pub fn findById(self: RepositoryPort, id: u128) !?ExampleEntity {
        return self.vtable.findById(self.context, id);
    }
    
    pub fn findAll(self: RepositoryPort, allocator: std.mem.Allocator) ![]ExampleEntity {
        return self.vtable.findAll(self.context, allocator);
    }
    
    pub fn save(self: RepositoryPort, entity: ExampleEntity) !void {
        return self.vtable.save(self.context, entity);
    }
    
    pub fn delete(self: RepositoryPort, id: u128) !void {
        return self.vtable.delete(self.context, id);
    }
};

// Domain service port
pub const ServicePort = struct {
    context: *anyopaque,
    vtable: *const VTable,
    
    pub const VTable = struct {
        get_example: *const fn (*anyopaque, u128) anyerror!?ExampleEntity,
        list_examples: *const fn (*anyopaque, std.mem.Allocator) anyerror![]ExampleEntity,
        create_example: *const fn (*anyopaque, []const u8, []const u8) anyerror!ExampleEntity,
        update_example: *const fn (*anyopaque, u128, []const u8) anyerror!?ExampleEntity,
        delete_example: *const fn (*anyopaque, u128) anyerror!void,
    };
    
    pub fn get_example(self: ServicePort, id: u128) !?ExampleEntity {
        return self.vtable.get_example(self.context, id);
    }
    
    pub fn list_examples(self: ServicePort, allocator: std.mem.Allocator) ![]ExampleEntity {
        return self.vtable.list_examples(self.context, allocator);
    }
    
    pub fn create_example(self: ServicePort, name: []const u8, description: []const u8) !ExampleEntity {
        return self.vtable.create_example(self.context, name, description);
    }
    
    pub fn update_example(self: ServicePort, id: u128, name: []const u8) !?ExampleEntity {
        return self.vtable.update_example(self.context, id, name);
    }
    
    pub fn delete_example(self: ServicePort, id: u128) !void {
        return self.vtable.delete_example(self.context, id);
    }
};

// Domain entity
pub const ExampleEntity = struct {
    id: u128,
    name: []const u8,
    description: []const u8,
    status: Status,
    created_at: i64,
    updated_at: i64,
    
    pub const Status = enum {
        pending,
        active,
        archived,
    };
    
    pub fn init(allocator: std.mem.Allocator, id: u128, name: []const u8, description: []const u8) !ExampleEntity {
        const now = std.time.timestamp();
        
        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);
        
        const desc_copy = try allocator.dupe(u8, description);
        
        return .{
            .id = id,
            .name = name_copy,
            .description = desc_copy,
            .status = .pending,
            .created_at = now,
            .updated_at = now,
        };
    }
    
    pub fn activate(self: ExampleEntity) ExampleEntity {
        var copy = self;
        if (copy.status == .pending) {
            copy.status = .active;
            copy.updated_at = std.time.timestamp();
        }
        return copy;
    }
    
    pub fn archive(self: ExampleEntity) ExampleEntity {
        var copy = self;
        if (copy.status != .archived) {
            copy.status = .archived;
            copy.updated_at = std.time.timestamp();
        }
        return copy;
    }
    
    pub fn updateName(self: ExampleEntity, allocator: std.mem.Allocator, new_name: []const u8) !ExampleEntity {
        var copy = self;
        copy.name = try allocator.dupe(u8, new_name);
        copy.updated_at = std.time.timestamp();
        return copy;
    }
    
    pub fn deinit(self: ExampleEntity, allocator: std.mem.Allocator) void {
        allocator.free(self.name);
        allocator.free(self.description);
    }
};

// Domain error
pub const DomainError = error{
    EntityNotFound,
    InvalidInput,
    AlreadyExists,
    BusinessRuleViolation,
    OutOfMemory,
};

/// Application service
pub const ExampleService = struct {
    allocator: std.mem.Allocator,
    repository: RepositoryPort,

    pub fn init(allocator: std.mem.Allocator, repository: RepositoryPort) ExampleService {
        return .{
            .allocator = allocator,
            .repository = repository,
        };
    }

    pub fn toPort(self: *ExampleService) ServicePort {
        return .{
            .context = self,
            .vtable = &.{
                .get_example = getExampleImpl,
                .list_examples = listExamplesImpl,
                .create_example = createExampleImpl,
                .update_example = updateExampleImpl,
                .delete_example = deleteExampleImpl,
            },
        };
    }

    fn getExampleImpl(ctx: *anyopaque, id: u128) !?ExampleEntity {
        const self: *ExampleService = @alignCast(@ptrCast(ctx));
        return self.repository.findById(id);
    }

    fn listExamplesImpl(ctx: *anyopaque, allocator: std.mem.Allocator) ![]ExampleEntity {
        const self: *ExampleService = @alignCast(@ptrCast(ctx));
        return self.repository.findAll(allocator);
    }

    fn createExampleImpl(ctx: *anyopaque, name: []const u8, description: []const u8) !ExampleEntity {
        const self: *ExampleService = @alignCast(@ptrCast(ctx));
        
        const id = std.crypto.random.int(u128);
        const entity = try ExampleEntity.init(self.allocator, id, name, description);
        
        try self.repository.save(entity);
        return entity;
    }

    fn updateExampleImpl(ctx: *anyopaque, id: u128, name: []const u8) !?ExampleEntity {
        const self: *ExampleService = @alignCast(@ptrCast(ctx));
        
        if (try self.repository.findById(id)) |entity| {
            const updated = try entity.updateName(self.allocator, name);
            try self.repository.save(updated);
            return updated;
        }
        return null;
    }

    fn deleteExampleImpl(ctx: *anyopaque, id: u128) !void {
        const self: *ExampleService = @alignCast(@ptrCast(ctx));
        try self.repository.delete(id);
    }
};

/// In-memory repository implementation
pub const InMemoryRepository = struct {
    allocator: std.mem.Allocator,
    data: std.AutoHashMap(u128, ExampleEntity),
    mutex: std.Thread.Mutex,

    pub fn init(allocator: std.mem.Allocator) InMemoryRepository {
        return .{
            .allocator = allocator,
            .data = std.AutoHashMap(u128, ExampleEntity).init(allocator),
            .mutex = std.Thread.Mutex{},
        };
    }

    pub fn deinit(self: *InMemoryRepository) void {
        var it = self.data.iterator();
        while (it.next()) |entry| {
            entry.value_ptr.deinit(self.allocator);
        }
        self.data.deinit();
    }

    pub fn toPort(self: *InMemoryRepository) RepositoryPort {
        return .{
            .context = self,
            .vtable = &.{
                .findById = findByIdImpl,
                .findAll = findAllImpl,
                .save = saveImpl,
                .delete = deleteImpl,
            },
        };
    }

    fn findByIdImpl(ctx: *anyopaque, id: u128) !?ExampleEntity {
        const self: *InMemoryRepository = @alignCast(@ptrCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();
        
        return self.data.get(id);
    }

    fn findAllImpl(ctx: *anyopaque, allocator: std.mem.Allocator) ![]ExampleEntity {
        const self: *InMemoryRepository = @alignCast(@ptrCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();
        
        var result = try allocator.alloc(ExampleEntity, self.data.count());
        var it = self.data.iterator();
        var i: usize = 0;
        while (it.next()) |entry| : (i += 1) {
            result[i] = entry.value_ptr.*;
        }
        return result;
    }

    fn saveImpl(ctx: *anyopaque, entity: ExampleEntity) !void {
        const self: *InMemoryRepository = @alignCast(@ptrCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();
        
        try self.data.put(entity.id, entity);
    }

    fn deleteImpl(ctx: *anyopaque, id: u128) !void {
        const self: *InMemoryRepository = @alignCast(@ptrCast(ctx));
        self.mutex.lock();
        defer self.mutex.unlock();
        
        _ = self.data.remove(id);
    }
};

/// Simple HTTP server
pub const HttpServer = struct {
    allocator: std.mem.Allocator,
    service: ServicePort,
    
    pub fn init(allocator: std.mem.Allocator, service: ServicePort) HttpServer {
        return .{
            .allocator = allocator,
            .service = service,
        };
    }
    
    pub fn start(_: *HttpServer, port: u16) !void {
        const address = std.net.Address.initIp4(.{ 127, 0, 0, 1 }, port);
        var server = try address.listen(.{
            .reuse_address = true,
        });
        defer server.deinit();
        
        std.log.info("Server listening on http://127.0.0.1:{d}", .{port});
        
        while (true) {
            var connection = try server.accept();
            defer connection.stream.close();
            
            var buf: [1024]u8 = undefined;
            const bytes_read = try connection.stream.read(&buf);
            if (bytes_read == 0) continue;
            
            // Simple routing
            const request = buf[0..bytes_read];
            if (std.mem.startsWith(u8, request, "GET /health")) {
                const response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}\n";
                _ = try connection.stream.write(response);
            } else if (std.mem.startsWith(u8, request, "GET /examples")) {
                const response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"examples\":[]}\n";
                _ = try connection.stream.write(response);
            } else {
                const response = "HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\n\r\n{\"error\":\"Not found\"}\n";
                _ = try connection.stream.write(response);
            }
        }
    }
};

/// Application entry point
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Initialize repository
    var repository = InMemoryRepository.init(allocator);
    defer repository.deinit();
    
    // Create service
    var service = ExampleService.init(allocator, repository.toPort());
    const service_port = service.toPort();
    
    // Create and start HTTP server
    var server = HttpServer.init(allocator, service_port);
    try server.start(3000);
}
