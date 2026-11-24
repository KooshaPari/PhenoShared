package domain

import (
	"testing"
	"time"
)

func TestNewEntityID(t *testing.T) {
	id1 := NewEntityID()
	id2 := NewEntityID()

	if id1 == id2 {
		t.Error("expected different entity IDs")
	}

	if id1.String() == "" {
		t.Error("expected non-empty entity ID string")
	}
}

func TestParseEntityID(t *testing.T) {
	original := NewEntityID()
	parsed, err := ParseEntityID(original.String())

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if parsed != original {
		t.Error("expected parsed ID to equal original")
	}
}

func TestParseEntityID_Invalid(t *testing.T) {
	_, err := ParseEntityID("invalid-uuid")

	if err == nil {
		t.Error("expected error for invalid UUID")
	}
}

func TestBaseEntity_ID(t *testing.T) {
	id := NewEntityID()
	entity := NewBaseEntity(id)

	if entity.ID() != id {
		t.Error("expected entity ID to match")
	}
}

func TestBaseEntity_Equals(t *testing.T) {
	id1 := NewEntityID()
	id2 := NewEntityID()

	entity1 := NewBaseEntity(id1)
	entity2 := NewBaseEntity(id1)
	entity3 := NewBaseEntity(id2)

	if !entity1.Equals(entity2) {
		t.Error("expected entities with same ID to be equal")
	}

	if entity1.Equals(entity3) {
		t.Error("expected entities with different IDs to not be equal")
	}

	if entity1.Equals(nil) {
		t.Error("expected nil comparison to return false")
	}
}

func TestBaseEntity_Touch(t *testing.T) {
	entity := NewBaseEntity(NewEntityID())
	original := entity.UpdatedAt()

	time.Sleep(time.Millisecond)
	entity.Touch()

	if !entity.UpdatedAt().After(original) {
		t.Error("expected updated timestamp to be after original")
	}
}

func TestBaseEntity_CreatedAt(t *testing.T) {
	entity := NewBaseEntity(NewEntityID())

	if entity.CreatedAt().IsZero() {
		t.Error("expected non-zero created timestamp")
	}
}

func TestDomainError(t *testing.T) {
	err := NewDomainError("TEST_ERROR", "test message")

	if err.Code != "TEST_ERROR" {
		t.Errorf("expected code TEST_ERROR, got %s", err.Code)
	}

	if err.Message != "test message" {
		t.Errorf("expected message 'test message', got %s", err.Message)
	}

	expected := "TEST_ERROR: test message"
	if err.Error() != expected {
		t.Errorf("expected '%s', got '%s'", expected, err.Error())
	}
}

func TestDomainError_WithError(t *testing.T) {
	inner := NewDomainError("INNER", "inner message")
	err := &DomainError{Code: "OUTER", Message: "outer message", Err: inner}

	if err.Unwrap() != inner {
		t.Error("expected Unwrap to return inner error")
	}
}

func TestNewDomainErrorf(t *testing.T) {
	err := NewDomainErrorf("FMT_ERR", "value %d: %s", 42, "test")

	expected := "FMT_ERR: value 42: test"
	if err.Error() != expected {
		t.Errorf("expected '%s', got '%s'", expected, err.Error())
	}
}

func TestErrNotFound(t *testing.T) {
	if ErrNotFound.Error() != "entity not found" {
		t.Errorf("expected 'entity not found', got '%s'", ErrNotFound.Error())
	}
}

func TestErrInvalidInput(t *testing.T) {
	if ErrInvalidInput.Error() != "invalid input" {
		t.Errorf("expected 'invalid input', got '%s'", ErrInvalidInput.Error())
	}
}

func TestErrConflict(t *testing.T) {
	if ErrConflict.Error() != "conflict" {
		t.Errorf("expected 'conflict', got '%s'", ErrConflict.Error())
	}
}
