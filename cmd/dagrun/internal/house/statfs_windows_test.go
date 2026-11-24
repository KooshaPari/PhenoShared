//go:build windows

package house

import "testing"

// TestDiskFreeReportsFreeBytes guards the Windows statfs path: before it was
// implemented, diskFree always returned an error and doctor silently omitted
// disk_free_bytes, so disk_full_imminent could never fire on Windows.
func TestDiskFreeReportsFreeBytes(t *testing.T) {
	dir := t.TempDir()
	free, err := diskFree(dir)
	if err != nil {
		t.Fatalf("diskFree(%q): %v", dir, err)
	}
	if free == 0 {
		t.Fatalf("diskFree(%q) = 0, want the free bytes of the volume", dir)
	}
}
