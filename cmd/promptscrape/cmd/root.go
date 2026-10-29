package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "promptscrape",
	Short: "Scrape full prompt timelines from JCode and Codex sessions",
	Long: `promptscrape extracts the full user prompt timeline from JCode and Codex harness sessions.

It auto-derives session ids from HTML files or falls back to the current session.
Only real human prompts are returned: harness-injected context and tool results
are filtered out. Output is formatted for curation, annotation, and labeling.`,
	SilenceUsage:  true,
	SilenceErrors: true,
}

// Execute runs the root command and returns any error to the caller.
func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.CompletionOptions.DisableDefaultCmd = false
}

// exitErr prints an error to stderr and exits non-zero.
//
// Deprecated: commands return errors instead. Kept for compatibility with
// older call sites.
func exitErr(err error) {
	fmt.Fprintf(os.Stderr, "Error: %v\n", err)
	os.Exit(1)
}
