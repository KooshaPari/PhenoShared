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

It auto-derives session IDs from HTML files or falls back to the current session.
Outputs are formatted for curation, annotation, and labeling.`,
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.CompletionOptions.DisableDefaultCmd = false
}

// Helper to exit with error
func exitErr(err error) {
	fmt.Fprintf(os.Stderr, "Error: %v\n", err)
	os.Exit(1)
}
