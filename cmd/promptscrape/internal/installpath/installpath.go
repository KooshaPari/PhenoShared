// Package installpath resolves where the promptscrape binary lives on disk.
//
// The same rules are shared by the install, uninstall, and update commands so
// they can never disagree about which file they are managing.
package installpath

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// BinaryName is the name of the installed executable.
func BinaryName() string {
	if runtime.GOOS == "windows" {
		return "promptscrape.exe"
	}
	return "promptscrape"
}

// Candidates returns the directories searched for an installed binary, in
// priority order.
func Candidates() []string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = ""
	}

	var dirs []string
	if home != "" {
		dirs = append(dirs, filepath.Join(home, ".local", "bin"))
		if runtime.GOOS == "windows" {
			dirs = append(dirs, filepath.Join(home, "AppData", "Local", "bin"))
			dirs = append(dirs, filepath.Join(home, "go", "bin"))
		}
	}
	if runtime.GOOS != "windows" {
		dirs = append(dirs, "/usr/local/bin")
	}
	return dirs
}

// Preferred returns the directory the binary should be installed into.
//
// ~/.local/bin wins when it already exists, because it is user-writable and
// needs no sudo. Otherwise a system directory is used.
func Preferred() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot determine home directory: %w", err)
	}

	localBin := filepath.Join(home, ".local", "bin")
	if _, err := os.Stat(localBin); err == nil {
		return localBin, nil
	}

	if runtime.GOOS == "windows" {
		return filepath.Join(home, "AppData", "Local", "bin"), nil
	}
	return "/usr/local/bin", nil
}

// Locate returns the path of an installed binary, or "" when none is found.
func Locate() string {
	for _, dir := range Candidates() {
		target := filepath.Join(dir, BinaryName())
		if _, err := os.Stat(target); err == nil {
			return target
		}
	}
	return ""
}
