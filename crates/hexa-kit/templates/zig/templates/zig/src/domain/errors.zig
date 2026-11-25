const std = @import("std");

/// Domain error types for the hexagonal architecture
pub const DomainError = error{
    /// Entity not found in repository
    EntityNotFound,
    /// Validation failed
    ValidationError,
    /// Business rule violated
    BusinessRuleViolation,
    /// Invalid state transition
    InvalidStateTransition,
    /// Duplicate entity
    DuplicateEntity,
    /// Unknown error
    Unknown,
};

/// Creates a detailed error with context
pub const ErrorContext = struct {
    code: DomainError,
    message: []const u8,
    field: ?[]const u8 = null,

    pub fn init(code: DomainError, message: []const u8) ErrorContext {
        return .{
            .code = code,
            .message = message,
            .field = null,
        };
    }

    pub fn withField(self: ErrorContext, field_name: []const u8) ErrorContext {
        return .{
            .code = self.code,
            .message = self.message,
            .field = field_name,
        };
    }
};
