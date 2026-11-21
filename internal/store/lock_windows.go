//go:build windows

package store

import (
	"os"
	"syscall"
	"unsafe"
)

// Windows has no flock(2), so this is the LockFileEx equivalent.
//
// The contract is deliberately identical to the unix implementation in
// lock_unix.go: it blocks until the caller holds an exclusive lock on the whole
// file, and the kernel releases it when the process dies. Windows file locks
// belong to the open handle, so they are released on Close or on process exit
// without any stale-lock cleanup path — the same property flock gives us.
//
// The calls are resolved lazily from kernel32 rather than pulling in
// golang.org/x/sys/windows, which keeps this module's single dependency (yaml)
// intact.
var (
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	procLockFileEx   = kernel32.NewProc("LockFileEx")
	procUnlockFileEx = kernel32.NewProc("UnlockFileEx")
)

const (
	// lockfileExclusiveLock gives an exclusive (writer) lock. Without
	// lockfileFailImmediately the call waits instead of returning
	// ERROR_LOCK_VIOLATION, which is what callers expect here.
	lockfileExclusiveLock = 0x00000002

	// lockfileWholeFileLow/High describe a byte range covering the file. This
	// mirrors flock, which locks the whole file rather than a byte range.
	lockfileWholeFileLow  = 0xFFFFFFFF
	lockfileWholeFileHigh = 0xFFFFFFFF
)

// overlapped is the Win32 OVERLAPPED structure. Only the offset fields matter
// for locking; the rest must be present and zeroed.
type overlapped struct {
	Internal     uintptr
	InternalHigh uintptr
	Offset       uint32
	OffsetHigh   uint32
	HEvent       syscall.Handle
}

// lockExclusive blocks until it holds an exclusive lock on f.
func lockExclusive(f *os.File) error {
	var ol overlapped
	r, _, err := procLockFileEx.Call(
		f.Fd(),
		uintptr(lockfileExclusiveLock),
		0,
		uintptr(lockfileWholeFileLow),
		uintptr(lockfileWholeFileHigh),
		uintptr(unsafe.Pointer(&ol)),
	)
	if r == 0 {
		return os.NewSyscallError("LockFileEx", err)
	}
	return nil
}

func unlock(f *os.File) error {
	var ol overlapped
	r, _, err := procUnlockFileEx.Call(
		f.Fd(),
		0,
		uintptr(lockfileWholeFileLow),
		uintptr(lockfileWholeFileHigh),
		uintptr(unsafe.Pointer(&ol)),
	)
	if r == 0 {
		return os.NewSyscallError("UnlockFileEx", err)
	}
	return nil
}
