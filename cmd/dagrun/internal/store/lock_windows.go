//go:build windows

package store

import (
	"errors"
	"os"
	"syscall"
	"unsafe"
)

// Windows has no flock(2), but it has the same guarantee under a different
// name: LockFileEx takes a mandatory byte-range lock that a second handle
// cannot take concurrently, and the kernel drops it when the owning handle
// closes, including when the process dies. That is the whole contract
// store.go depends on -- "the kernel releases it if the process dies, so there
// is no stale-lock cleanup path anywhere in this codebase" -- so the Unix case
// maps onto it one-for-one.
//
// The calls go straight to kernel32 through the stdlib syscall package rather
// than adding golang.org/x/sys: this module has exactly one dependency
// (yaml.v3) on purpose, and a two-function shim is not worth a second one.

var (
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	procLockFileEx   = kernel32.NewProc("LockFileEx")
	procUnlockFileEx = kernel32.NewProc("UnlockFileEx")
)

const (
	// lockfileExclusiveLock blocks while another handle holds an overlapping
	// range. Without it LockFileEx takes a shared lock, which would let two
	// writers in -- exactly the unsafe mode this file exists to prevent.
	// lockfileFailImmediately is deliberately not used: the Unix path blocks,
	// so Windows blocks too.
	lockfileExclusiveLock = 0x00000002

	// Windows locks a (offset, length) range, not "the file". Every dagrun
	// lock site locks offset 0, so a single maximal span covers the file
	// without needing its size.
	lockWholeLow  = 0xFFFFFFFF
	lockWholeHigh = 0xFFFFFFFF
)

// lockExclusive blocks until it holds an exclusive lock on the whole of f.
// It returns the kernel's error if the lock cannot be taken for a reason other
// than contention (the handle was opened without write access, say).
func lockExclusive(f *os.File) error {
	var ol syscall.Overlapped // offset 0, hEvent nil: wait on this thread
	r1, _, err := procLockFileEx.Call(
		f.Fd(),
		lockfileExclusiveLock,
		0,
		lockWholeLow,
		lockWholeHigh,
		uintptr(unsafe.Pointer(&ol)),
	)
	if r1 == 0 {
		if err == nil || errors.Is(err, syscall.Errno(0)) {
			return os.NewSyscallError("LockFileEx", syscall.EINVAL)
		}
		return os.NewSyscallError("LockFileEx", err)
	}
	return nil
}

func unlock(f *os.File) error {
	var ol syscall.Overlapped
	r1, _, err := procUnlockFileEx.Call(
		f.Fd(),
		0,
		lockWholeLow,
		lockWholeHigh,
		uintptr(unsafe.Pointer(&ol)),
	)
	if r1 == 0 {
		if err == nil || errors.Is(err, syscall.Errno(0)) {
			return os.NewSyscallError("UnlockFileEx", syscall.EINVAL)
		}
		return os.NewSyscallError("UnlockFileEx", err)
	}
	return nil
}
