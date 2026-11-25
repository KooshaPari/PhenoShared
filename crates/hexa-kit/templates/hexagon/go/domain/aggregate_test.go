package domain

import (
	"testing"
	"time"
)

type testEvent struct {
	BaseDomainEvent
	data string
}

func (e *testEvent) EventType() string {
	return "test.event"
}

func TestNewBaseAggregate(t *testing.T) {
	id := NewEntityID()
	agg := NewBaseAggregate(id)

	if agg.ID() != id {
		t.Error("expected aggregate ID to match")
	}

	if agg.Version() != 1 {
		t.Errorf("expected version 1, got %d", agg.Version())
	}

	if len(agg.PullEvents()) != 0 {
		t.Error("expected no pending events")
	}
}

func TestBaseAggregate_AddEvent(t *testing.T) {
	id := NewEntityID()
	agg := NewBaseAggregate(id)
	initialVersion := agg.Version()

	event := &testEvent{
		BaseDomainEvent: *NewBaseDomainEvent("test.event", id),
		data:            "test",
	}

	agg.AddEvent(event)

	if agg.Version() != initialVersion+1 {
		t.Errorf("expected version %d, got %d", initialVersion+1, agg.Version())
	}

	events := agg.PullEvents()
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}

	if events[0].EventType() != "test.event" {
		t.Errorf("expected event type 'test.event', got '%s'", events[0].EventType())
	}

	// PullEvents should clear pending events
	if len(agg.PullEvents()) != 0 {
		t.Error("expected no pending events after pull")
	}
}

func TestBaseAggregate_AddEvent_Multiple(t *testing.T) {
	id := NewEntityID()
	agg := NewBaseAggregate(id)

	for i := 0; i < 5; i++ {
		event := &testEvent{
			BaseDomainEvent: *NewBaseDomainEvent("test.event", id),
			data:            "test",
		}
		agg.AddEvent(event)
	}

	events := agg.PullEvents()
	if len(events) != 5 {
		t.Errorf("expected 5 events, got %d", len(events))
	}

	if agg.Version() != 6 { // 1 initial + 5 added
		t.Errorf("expected version 6, got %d", agg.Version())
	}
}

func TestNewTime(t *testing.T) {
	before := time.Now().Unix()
	tm := NewTime()
	after := time.Now().Unix()

	if tm.Unix() < before || tm.Unix() > after {
		t.Error("time should be within expected range")
	}
}

func TestFromTime(t *testing.T) {
	original := time.Date(2024, 1, 15, 10, 30, 0, 0, time.UTC)
	tm := FromTime(original)

	if tm.Unix() != original.Unix() {
		t.Errorf("expected %d, got %d", original.Unix(), tm.Unix())
	}

	converted := tm.ToTime()
	if !converted.Equal(original) {
		t.Errorf("expected %v, got %v", original, converted)
	}
}

func TestTime_RoundTrip(t *testing.T) {
	original := time.Now()
	tm := FromTime(original)
	converted := tm.ToTime()

	// Compare Unix timestamps (monotonic clock info may be lost)
	if tm.Unix() != converted.Unix() || tm.Unix() != original.Unix() {
		t.Errorf("expected Unix %d, got %d (tm) and %d (converted)", original.Unix(), tm.Unix(), converted.Unix())
	}
}

func TestNewBaseDomainEvent(t *testing.T) {
	id := NewEntityID()
	event := NewBaseDomainEvent("user.created", id)

	if event.EventType() != "user.created" {
		t.Errorf("expected 'user.created', got '%s'", event.EventType())
	}

	if event.AggregateID() != id {
		t.Error("expected aggregate ID to match")
	}

	if event.OccurredAt().Unix() == 0 {
		t.Error("expected non-zero occurrence time")
	}
}

func TestBaseDomainEvent_WithMetadata(t *testing.T) {
	id := NewEntityID()
	event := NewBaseDomainEvent("test", id)

	event.WithMetadata("key1", "value1")
	event.WithMetadata("key2", "value2")

	if event.GetMetadata("key1") != "value1" {
		t.Error("expected key1=value1")
	}

	if event.GetMetadata("key2") != "value2" {
		t.Error("expected key2=value2")
	}

	if event.GetMetadata("nonexistent") != "" {
		t.Error("expected empty for nonexistent key")
	}
}
