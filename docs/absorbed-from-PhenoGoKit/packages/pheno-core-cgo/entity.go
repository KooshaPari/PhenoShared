// Package phenocore provides CGO bindings to Rust phenotype-core
package phenocore

/*
#include <stdlib.h>
#include <stdbool.h>

// Forward declarations for Rust FFI
extern char* entity_id_new(const char* id, const char* namespace);
extern void entity_id_free(char* ptr);
extern bool entity_id_validate(const char* id, const char* namespace);
extern char* entity_id_to_json(const char* id, const char* namespace);
*/
import "C"
import (
	"fmt"
	"unsafe"
)

// EntityId represents a typed identifier in the system
type EntityId struct {
	ID        string
	Namespace string
}

// NewEntityId creates a new EntityId
func NewEntityId(id, namespace string) *EntityId {
	return &EntityId{
		ID:        id,
		Namespace: namespace,
	}
}

// Validate checks if the EntityId is valid via Rust FFI
func (e *EntityId) Validate() bool {
	cid := C.CString(e.ID)
	cns := C.CString(e.Namespace)
	defer C.free(unsafe.Pointer(cid))
	defer C.free(unsafe.Pointer(cns))

	return bool(C.entity_id_validate(cid, cns))
}

// ToJSON serializes EntityId to JSON via Rust FFI
func (e *EntityId) ToJSON() (string, error) {
	cid := C.CString(e.ID)
	cns := C.CString(e.Namespace)
	defer C.free(unsafe.Pointer(cid))
	defer C.free(unsafe.Pointer(cns))

	jsonPtr := C.entity_id_to_json(cid, cns)
	if jsonPtr == nil {
		return "", fmt.Errorf("failed to serialize EntityId")
	}
	defer C.entity_id_free(jsonPtr)

	return C.GoString(jsonPtr), nil
}

// String implements Stringer interface
func (e *EntityId) String() string {
	return fmt.Sprintf("EntityId(id=%s, namespace=%s)", e.ID, e.Namespace)
}
