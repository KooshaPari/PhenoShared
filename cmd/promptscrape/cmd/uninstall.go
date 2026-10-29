package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/spf13/cobra"
)

var uninstallCmd = &cobra.Command{
	Use:   "uninstall",
	Short: "Uninstall promptscrape from system",
	Run: func(cmd *cobra.Command, args []string) {
		home, _ := os.UserHomeDir()
		var installDirs []string
		installDirs = append(installDirs, filepath.Join(home, ".local", "bin"))
		if runtime.GOOS == "windows" {
			installDirs = append(installDirs, filepath.Join(home, "AppData", "Local", "bin"))
		} else {
			installDirs = append(installDirs, "/usr/local/bin")
		}

		removed := false
		for _, dir := range installDirs {
			target := filepath.Join(dir, "promptscrape")
			if runtime.GOOS == "windows" {
				target += ".exe"
			}
			if _, err := os.Stat(target); err == nil {
				if err := os.Remove(target); err != nil {
					fmt.Fprintf(cmd.ErrOrStderr(), "Failed to remove %s: %v\n", target, err)
				} else {
					fmt.Printf("Removed %s\n", target)
					removed = true
				}
			}
		}

		if !removed {
			fmt.Println("promptscrape not found in common install locations")
		}
	},
}

func init() {
	rootCmd.AddCommand(uninstallCmd)
}
