package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/spf13/cobra"
)

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "Install promptscrape to system PATH",
	Long:  "Install the promptscrape binary to ~/.local/bin or /usr/local/bin",
	Run: func(cmd *cobra.Command, args []string) {
		// Find current binary
		execPath, err := os.Executable()
		if err != nil {
			exitErr(fmt.Errorf("failed to find executable: %w", err))
		}

		// Determine install dir
		var installDir string
		home, _ := os.UserHomeDir()
		localBin := filepath.Join(home, ".local", "bin")
		if _, err := os.Stat(localBin); err == nil {
			installDir = localBin
		} else {
			if runtime.GOOS == "windows" {
				installDir = filepath.Join(home, "AppData", "Local", "bin")
			} else {
				installDir = "/usr/local/bin"
			}
		}

		if err := os.MkdirAll(installDir, 0755); err != nil {
			exitErr(fmt.Errorf("failed to create install dir: %w", err))
		}

		target := filepath.Join(installDir, "promptscrape")
		if runtime.GOOS == "windows" {
			target += ".exe"
		}

		// Copy binary
		data, err := os.ReadFile(execPath)
		if err != nil {
			exitErr(fmt.Errorf("failed to read binary: %w", err))
		}

		if err := os.WriteFile(target, data, 0755); err != nil {
			exitErr(fmt.Errorf("failed to install: %w", err))
		}

		fmt.Printf("Installed to %s\n", target)
		fmt.Printf("Make sure %s is in your PATH\n", installDir)
	},
}

func init() {
	rootCmd.AddCommand(installCmd)
}
