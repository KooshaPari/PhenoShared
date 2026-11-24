const std = @import("std");
const net = std.net;
const http = std.http;
const ports = @import("../domain/ports.zig");
const ServicePort = ports.ServicePort;
const Entity = @import("../domain/entity.zig").ExampleEntity;

/// Simple HTTP server adapter for the Zig service
pub const HttpServer = struct {
    allocator: std.mem.Allocator,
    service: ServicePort,
    server: net.Server,

    pub fn init(allocator: std.mem.Allocator, service: ServicePort, port: u16) !HttpServer {
        const address = try net.Address.parseIp("0.0.0.0", port);
        const server = try net.Server.init(address, .{ .reuse_address = true });

        return .{
            .allocator = allocator,
            .service = service,
            .server = server,
        };
    }

    pub fn deinit(self: *HttpServer) void {
        self.server.deinit();
    }

    pub fn start(self: *HttpServer) !void {
        std.log.info("Server listening on :{d}", .{self.server.listen_address.getPort()});

        while (true) {
            const conn = try self.server.accept();
            try self.handleConnection(conn);
            conn.stream.close();
        }
    }

    fn handleConnection(self: *HttpServer, conn: net.Server.Connection) !void {
        var buf: [4096]u8 = undefined;
        const read_len = try conn.stream.read(&buf);
        if (read_len == 0) return;

        const request = buf[0..read_len];
        
        // Simple path routing
        if (std.mem.startsWith(u8, request, "GET /health")) {
            try self.sendResponse(conn, 200, "OK", "{\"status\":\"healthy\"}");
        } else if (std.mem.startsWith(u8, request, "GET /examples")) {
            try self.handleListExamples(conn);
        } else {
            try self.sendResponse(conn, 404, "Not Found", "{\"error\":\"Not Found\"}");
        }
    }

    fn handleListExamples(self: *HttpServer, conn: net.Server.Connection) !void {
        const examples = self.service.listExamples(self.allocator) catch |err| {
            try self.sendResponse(conn, 500, "Internal Server Error", "{\"error\":\"Internal error\"}");
            return;
        };
        defer self.allocator.free(examples);

        // Simple JSON serialization
        var buf = std.ArrayList(u8).init(self.allocator);
        defer buf.deinit();

        try buf.appendSlice("[");
        for (examples, 0..) |entity, i| {
            if (i > 0) try buf.appendSlice(",");
            try std.json.stringify(entity, .{}, buf.writer());
        }
        try buf.appendSlice("]");

        try self.sendResponse(conn, 200, "OK", buf.items);
    }

    fn sendResponse(self: HttpServer, conn: net.Server.Connection, status_code: u16, status_text: []const u8, body: []const u8) !void {
        const response = try std.fmt.allocPrint(self.allocator, 
            "HTTP/1.1 {d} {s}\r\nContent-Type: application/json\r\nContent-Length: {d}\r\n\r\n{s}",
            .{ status_code, status_text, body.len, body }
        );
        defer self.allocator.free(response);

        _ = try conn.stream.write(response);
    }
};
