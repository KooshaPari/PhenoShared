//go:build windows

package house

import (
	"fmt"
	"syscall"
	"unsafe"
)

// syscallStatfs carries the same two fields the unix build fills, so
// diskFree (Bavail * Bsize) computes free bytes on both platforms.
type syscallStatfs struct {
	Bsize  uint64
	Bavail uint64
}

var (
	kernel32               = syscall.NewLazyDLL("kernel32.dll")
	procGetDiskFreeSpaceEx = kernel32.NewProc("GetDiskFreeSpaceExW")
)

// statfs reports the free space available to the calling user on the volume
// holding path, via GetDiskFreeSpaceExW.
//
// Bsize is set to 1 because the API already reports bytes, and Bavail is left
// as the bytes available to this user (the same figure df prints), so the shared
// Bsize*Bavail arithmetic in diskFree stays correct without a second code path.
func statfs(path string, st *syscallStatfs) error {
	p, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return err
	}
	var availToUser, total, totalFree uint64
	r1, _, callErr := procGetDiskFreeSpaceEx.Call(
		uintptr(unsafe.Pointer(p)),
		uintptr(unsafe.Pointer(&availToUser)),
		uintptr(unsafe.Pointer(&total)),
		uintptr(unsafe.Pointer(&totalFree)),
	)
	if r1 == 0 {
		return fmt.Errorf("GetDiskFreeSpaceExW %q: %w", path, callErr)
	}
	st.Bsize = 1
	st.Bavail = availToUser
	return nil
}
