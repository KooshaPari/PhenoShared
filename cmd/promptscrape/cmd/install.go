package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/KooshaPari/PhenoShared/cmd/promptscrape/internal/installpath"
	"github.com/spf13/cobra"
)

var installDir string

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "Install promptscrape into a PATH directory",
	Long: `Copy the running promptscrape binary into a directory on your PATH.

The default target is ~/.local/bin when it exists, otherwise /usr/local/bin
(on Windows, %LOCALAPPDATA%\bin). Use --dir to override.`,
	Example: `  promptscrape install
  promptscrape install --dir ~/.local/bin`,
	RunE: func(cmd *cobra.Command, args []string) error {
		execPath, err := os.Executable()
		if err != nil {
			return fmt.Errorf("cannot locate the running binary: %w", err)
		}

		dir := installDir
		if dir == "" {
			dir, err = installpath.Preferred()
			if err != nil {
				return err
			}
		}

		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Errorf("cannot create %s: %w", dir, err)
		}

		target := filepath.Join(dir, installpath.BinaryName())
		if err := copyExecutable(execPath, target); err != nil {
			return err
		}

		fmt.Fprintf(cmd.OutOrStdout(), "Installed %s\n", target)
		if !onPath(dir) {
			fmt.Fprintf(cmd.OutOrStdout(), "Note: %s is not on your PATH. Add it with:\n", dir)
			fmt.Fprintf(cmd.OutOrStdout(), "  export PATH=\"%s:$PATH\"\n", dir)
		}
		return nil
	},
}

// copyExecutable copies src to dst, preserving the executable bit.
func copyExecutable(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return fmt.Errorf("cannot read %s: %w", src, err)
	}
	mode := os.FileMode(0o755)
	if info, err := os.Stat(src); err == nil {
		mode = info.Mode().Perm()
	}
	if err := os.WriteFile(dst, data, mode); err != nil {
		return fmt.Errorf("cannot write %s: %w", dst, err)
	}
	return nil
}

// onPath reports whether dir appears in the PATH environment variable.
func onPath(dir string) bool {
	for _, p := range filepath.SplitList(os.Getenv("PATH")) {
		if p == dir {
			return true
		}
	}
	return false
}

func init() {
	rootCmd.AddCommand(installCmd)
	installCmd.Flags().StringVar(&installDir, "dir", "", "Directory to install into (default: ~/.local/bin or /usr/local/bin)")
}
