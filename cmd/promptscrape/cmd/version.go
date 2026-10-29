package cmd

import (
	"fmt"
	"runtime"

	"github.com/spf13/cobra"
)

// Build metadata, injected at link time:
//
//	go build -ldflags "-X github.com/KooshaPari/PhenoShared/cmd/promptscrape/cmd.version=1.2.3"
var (
	version = "0.1.0-dev"
	commit  = "unknown"
	date    = "unknown"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print version information",
	RunE: func(cmd *cobra.Command, args []string) error {
		out := cmd.OutOrStdout()
		fmt.Fprintf(out, "promptscrape %s\n", version)
		fmt.Fprintf(out, "  commit: %s\n", commit)
		fmt.Fprintf(out, "  built:  %s\n", date)
		fmt.Fprintf(out, "  go:     %s\n", runtime.Version())
		fmt.Fprintf(out, "  platform: %s/%s\n", runtime.GOOS, runtime.GOARCH)
		return nil
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
