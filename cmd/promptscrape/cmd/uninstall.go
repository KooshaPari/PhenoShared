package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/KooshaPari/PhenoShared/cmd/promptscrape/internal/installpath"
	"github.com/spf13/cobra"
)

var uninstallCmd = &cobra.Command{
	Use:   "uninstall",
	Short: "Remove the installed promptscrape binary",
	Long: `Remove the promptscrape binary from every known install location.

Searched locations: ~/.local/bin, /usr/local/bin, and on Windows
%LOCALAPPDATA%\bin plus %USERPROFILE%\go\bin.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		removed := []string{}
		for _, dir := range installpath.Candidates() {
			target := filepath.Join(dir, installpath.BinaryName())
			if _, err := os.Stat(target); err != nil {
				continue
			}
			if err := os.Remove(target); err != nil {
				fmt.Fprintf(cmd.ErrOrStderr(), "cannot remove %s: %v\n", target, err)
				continue
			}
			removed = append(removed, target)
		}

		if len(removed) == 0 {
			fmt.Fprintln(cmd.OutOrStdout(), "promptscrape was not found in any known install location")
			return nil
		}
		for _, path := range removed {
			fmt.Fprintf(cmd.OutOrStdout(), "Removed %s\n", path)
		}
		return nil
	},
}

func init() {
	rootCmd.AddCommand(uninstallCmd)
}
