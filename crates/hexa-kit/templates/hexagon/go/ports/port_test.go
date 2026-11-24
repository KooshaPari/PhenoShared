package ports

import (
	"context"
	"testing"
)

func TestNewFilter(t *testing.T) {
	filter := NewFilter()

	if filter.Limit != 100 {
		t.Errorf("expected default limit 100, got %d", filter.Limit)
	}

	if filter.Offset != 0 {
		t.Error("expected default offset 0")
	}

	if filter.Conditions == nil {
		t.Error("expected non-nil conditions slice")
	}
}

func TestFilter_WithCondition(t *testing.T) {
	filter := NewFilter()

	filter.WithCondition("name", OpEq, "test")
	filter.WithCondition("age", OpGt, 18)

	if len(filter.Conditions) != 2 {
		t.Errorf("expected 2 conditions, got %d", len(filter.Conditions))
	}

	if filter.Conditions[0].Field != "name" {
		t.Errorf("expected field 'name', got '%s'", filter.Conditions[0].Field)
	}

	if filter.Conditions[0].Operator != OpEq {
		t.Errorf("expected operator 'eq', got '%s'", filter.Conditions[0].Operator)
	}

	if filter.Conditions[0].Value != "test" {
		t.Errorf("expected value 'test', got '%v'", filter.Conditions[0].Value)
	}
}

func TestFilter_WithCondition_Fluent(t *testing.T) {
	filter := NewFilter().
		WithCondition("name", OpEq, "test").
		WithCondition("age", OpGte, 21).
		WithCondition("status", OpIn, []string{"active", "pending"})

	if len(filter.Conditions) != 3 {
		t.Errorf("expected 3 conditions, got %d", len(filter.Conditions))
	}
}

func TestFilter_WithLimit(t *testing.T) {
	filter := NewFilter().WithLimit(50)

	if filter.Limit != 50 {
		t.Errorf("expected limit 50, got %d", filter.Limit)
	}
}

func TestFilter_WithOffset(t *testing.T) {
	filter := NewFilter().WithOffset(100)

	if filter.Offset != 100 {
		t.Errorf("expected offset 100, got %d", filter.Offset)
	}
}

func TestFilter_Chained(t *testing.T) {
	filter := NewFilter().
		WithCondition("active", OpEq, true).
		WithLimit(25).
		WithOffset(50)

	if len(filter.Conditions) != 1 {
		t.Error("expected 1 condition")
	}

	if filter.Limit != 25 {
		t.Errorf("expected limit 25, got %d", filter.Limit)
	}

	if filter.Offset != 50 {
		t.Errorf("expected offset 50, got %d", filter.Offset)
	}
}

func TestOperators(t *testing.T) {
	tests := []struct {
		op      Operator
		Display string
	}{
		{OpEq, "eq"},
		{OpNe, "ne"},
		{OpGt, "gt"},
		{OpLt, "lt"},
		{OpGte, "gte"},
		{OpLte, "lte"},
		{OpContains, "contains"},
		{OpStartsWith, "startsWith"},
		{OpIn, "in"},
	}

	for _, tt := range tests {
		t.Run(string(tt.op), func(t *testing.T) {
			if string(tt.op) != tt.Display {
				t.Errorf("expected %s, got %s", tt.Display, string(tt.op))
			}
		})
	}
}

func TestHealthStatus(t *testing.T) {
	status := HealthStatus{
		Status:  "healthy",
		Message: "all systems operational",
	}

	if status.Status != "healthy" {
		t.Errorf("expected 'healthy', got '%s'", status.Status)
	}

	if status.Message != "all systems operational" {
		t.Errorf("unexpected message: %s", status.Message)
	}
}

// Mock implementations for interface testing
type mockRepository struct {
	saved      map[string]any
	shouldFail bool
}

func (m *mockRepository) Save(ctx context.Context, entity any) (any, error) {
	if m.shouldFail {
		return nil, context.DeadlineExceeded
	}
	return entity, nil
}

func (m *mockRepository) FindByID(ctx context.Context, id string) (any, error) {
	if m.shouldFail {
		return nil, context.DeadlineExceeded
	}
	return m.saved[id], nil
}

func (m *mockRepository) Delete(ctx context.Context, id string) error {
	if m.shouldFail {
		return context.DeadlineExceeded
	}
	delete(m.saved, id)
	return nil
}

func (m *mockRepository) FindAll(ctx context.Context) ([]any, error) {
	if m.shouldFail {
		return nil, context.DeadlineExceeded
	}
	result := make([]any, 0, len(m.saved))
	for _, v := range m.saved {
		result = append(result, v)
	}
	return result, nil
}

func TestRepositoryInterface(t *testing.T) {
	repo := &mockRepository{
		saved: make(map[string]any),
	}

	ctx := context.Background()

	// Test that Save returns the entity (mock doesn't store by key)
	entity, err := repo.Save(ctx, "test-entity")
	if err != nil {
		t.Fatalf("unexpected save error: %v", err)
	}
	if entity != "test-entity" {
		t.Errorf("expected 'test-entity', got %v", entity)
	}

	// Test FindByID with empty key returns nil
	found, err := repo.FindByID(ctx, "")
	if err != nil {
		t.Fatalf("unexpected find error: %v", err)
	}
	if found != nil {
		t.Errorf("expected nil for empty key, got %v", found)
	}

	// Test FindAll with empty repository
	all, err := repo.FindAll(ctx)
	if err != nil {
		t.Fatalf("unexpected findall error: %v", err)
	}
	if len(all) != 0 {
		t.Errorf("expected 0 entities in empty repo, got %d", len(all))
	}

	// Test Delete with empty key succeeds
	err = repo.Delete(ctx, "")
	if err != nil {
		t.Fatalf("unexpected delete error: %v", err)
	}

	// Test error propagation
	failRepo := &mockRepository{shouldFail: true}
	_, err = failRepo.Save(ctx, "test")
	if err == nil {
		t.Error("expected error when shouldFail is true")
	}
}

func TestUnitOfWorkInterface(t *testing.T) {
	// Test that UnitOfWork interface methods exist and are callable
	uow := NewMockUnitOfWork()

	ctx := context.Background()

	if err := uow.Begin(ctx); err != nil {
		t.Errorf("unexpected Begin error: %v", err)
	}

	if err := uow.Commit(ctx); err != nil {
		t.Errorf("unexpected Commit error: %v", err)
	}

	if err := uow.Rollback(ctx); err != nil {
		t.Errorf("unexpected Rollback error: %v", err)
	}
}

// MockUnitOfWork implements UnitOfWork for testing
type mockUnitOfWork struct {
	committed  bool
	rolledBack bool
}

func NewMockUnitOfWork() *mockUnitOfWork {
	return &mockUnitOfWork{}
}

func (m *mockUnitOfWork) Begin(ctx context.Context) error {
	return nil
}

func (m *mockUnitOfWork) Commit(ctx context.Context) error {
	m.committed = true
	return nil
}

func (m *mockUnitOfWork) Rollback(ctx context.Context) error {
	m.rolledBack = true
	return nil
}

func (m *mockUnitOfWork) GetRepository(entityName string) any {
	return nil
}
