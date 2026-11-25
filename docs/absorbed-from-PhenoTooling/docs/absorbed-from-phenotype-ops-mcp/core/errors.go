package core

import "fmt"

// WrappedError annotates lower-level failures with the calling operation.
type WrappedError struct {
	Op  string
	Err error
}

func (e WrappedError) Error() string {
	if e.Err == nil {
		return e.Op
	}
	return fmt.Sprintf("%s: %v", e.Op, e.Err)
}

func (e WrappedError) Unwrap() error {
	return e.Err
}
