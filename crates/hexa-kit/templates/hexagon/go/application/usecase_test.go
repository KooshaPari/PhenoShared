package application

import (
	"context"
	"errors"
	"testing"
)

func TestUseCaseFunc_Execute(t *testing.T) {
	uc := UseCaseFunc[string, int](func(ctx context.Context, input string) (int, error) {
		return len(input), nil
	})

	result, err := uc.Execute(context.Background(), "hello")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != 5 {
		t.Errorf("expected 5, got %d", result)
	}
}

func TestCommandFunc_Execute(t *testing.T) {
	// Create a command with payload
	cmd := NewCommand("user.create", map[string]interface{}{
		"email": "test@example.com",
		"name":  "Test User",
	})

	uc := CommandFunc[*Command, *DTO[string]](func(ctx context.Context, command *Command) (*DTO[string], error) {
		if command.Type != "user.create" {
			t.Errorf("expected type 'user.create', got '%s'", command.Type)
		}
		return NewDTO("created:" + command.Payload["email"].(string)), nil
	})

	result, err := uc.Execute(context.Background(), cmd)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Data != "created:test@example.com" {
		t.Errorf("unexpected data: %s", result.Data)
	}
}

func TestQueryFunc_Execute(t *testing.T) {
	query := NewQuery("user.get")
	query.WithFilter(QueryFilter{
		Field:    "id",
		Operator: "eq",
		Value:    "123",
	})

	uc := QueryFunc[*Query, *DTO[string]](func(ctx context.Context, q *Query) (*DTO[string], error) {
		if q.Type != "user.get" {
			t.Errorf("expected type 'user.get', got '%s'", q.Type)
		}
		if len(q.Filters) != 1 {
			t.Errorf("expected 1 filter, got %d", len(q.Filters))
		}
		return NewDTO("user:123"), nil
	})

	result, err := uc.Execute(context.Background(), query)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Data != "user:123" {
		t.Errorf("unexpected data: %s", result.Data)
	}
}

func TestCommandHandler_Handle(t *testing.T) {
	uc := CommandFunc[*Command, *DTO[string]](func(ctx context.Context, command *Command) (*DTO[string], error) {
		return NewDTO("handled"), nil
	})

	handler := NewCommandHandler(uc)
	result, err := handler.Handle(context.Background(), NewCommand("test", nil))

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Data != "handled" {
		t.Errorf("expected 'handled', got '%s'", result.Data)
	}
}

func TestQueryHandler_Handle(t *testing.T) {
	uc := QueryFunc[*Query, *DTO[string]](func(ctx context.Context, query *Query) (*DTO[string], error) {
		return NewDTO("queried"), nil
	})

	handler := NewQueryHandler(uc)
	result, err := handler.Handle(context.Background(), NewQuery("test"))

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Data != "queried" {
		t.Errorf("expected 'queried', got '%s'", result.Data)
	}
}

func TestUseCase_ErrorPropagation(t *testing.T) {
	expectedErr := errors.New("test error")
	uc := UseCaseFunc[string, int](func(ctx context.Context, input string) (int, error) {
		return 0, expectedErr
	})

	_, err := uc.Execute(context.Background(), "hello")
	if err != expectedErr {
		t.Errorf("expected error to be propagated, got %v", err)
	}
}

func TestApplicationError(t *testing.T) {
	err := NewApplicationError("TEST_CODE", "test message")

	if err.Code != "TEST_CODE" {
		t.Errorf("expected code 'TEST_CODE', got '%s'", err.Code)
	}

	if err.Message != "test message" {
		t.Errorf("expected message 'test message', got '%s'", err.Message)
	}

	expected := "TEST_CODE: test message"
	if err.Error() != expected {
		t.Errorf("expected '%s', got '%s'", expected, err.Error())
	}
}

func TestApplicationError_WithInnerError(t *testing.T) {
	inner := errors.New("inner error")
	err := &ApplicationError{Code: "OUTER", Message: "outer message", Err: inner}

	if err.Unwrap() != inner {
		t.Error("expected Unwrap to return inner error")
	}

	if err.Error() != "OUTER: outer message - inner error" {
		t.Errorf("unexpected error string: %s", err.Error())
	}
}

func TestDTO_Types(t *testing.T) {
	// Test NewDTO
	dto := NewDTO("test-data")
	if dto.Data != "test-data" {
		t.Errorf("expected 'test-data', got '%s'", dto.Data)
	}
	if dto.Meta.Timestamp.IsZero() {
		t.Error("expected non-zero timestamp")
	}

	// Test NewPaginated
	paged := NewPaginated(2, 10, 55)
	if paged.Page != 2 {
		t.Errorf("expected page 2, got %d", paged.Page)
	}
	if paged.TotalPages != 6 {
		t.Errorf("expected 6 total pages, got %d", paged.TotalPages)
	}

	// Test Command
	cmd := NewCommand("test.type", map[string]interface{}{"key": "value"})
	cmd.WithMetadata("request-id", "123")
	if cmd.Type != "test.type" {
		t.Errorf("expected 'test.type', got '%s'", cmd.Type)
	}
	if cmd.Metadata["request-id"] != "123" {
		t.Error("expected metadata to be set")
	}

	// Test Query
	q := NewQuery("test.query")
	q.WithFilter(QueryFilter{Field: "name", Operator: "eq", Value: "test"})
	if len(q.Filters) != 1 {
		t.Errorf("expected 1 filter, got %d", len(q.Filters))
	}

	// Test Pagination
	p := NewPagination(5, 50)
	if p.Page != 5 {
		t.Errorf("expected page 5, got %d", p.Page)
	}
	if p.PageSize != 50 {
		t.Errorf("expected page size 50, got %d", p.PageSize)
	}

	// Test Pagination bounds
	p = NewPagination(0, 200)
	if p.Page != 1 {
		t.Errorf("expected page 1 (minimum), got %d", p.Page)
	}
	if p.PageSize != 100 {
		t.Errorf("expected page size 100 (maximum), got %d", p.PageSize)
	}
}
