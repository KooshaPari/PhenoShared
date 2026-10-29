package cmd

import (
	"fmt"

	"github.com/phenotype/phenoShared/cmd/promptscrape/internal/extract"
	"github.com/phenotype/phenoShared/cmd/promptscrape/internal/resolve"
	"github.com/spf13/cobra"
)

var (
	htmlPath  string
	sessionID string
	outputFmt string
)

var scrapeCmd = &cobra.Command{
	Use:   "scrape [html-path]",
	Short: "Scrape prompt timeline from a session",
	Long: `Scrape the full user prompt timeline from JCode or Codex sessions.

Session ID is auto-derived from HTML if provided, or from current environment/cwd.
Supports both JCode sessions and Codex thread IDs.`,
	Args: cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			htmlPath = args[0]
		}

		sid := sessionID
		if sid == "" && htmlPath != "" {
			resolved, err := resolve.FromHTML(htmlPath)
			if err != nil {
				exitErr(err)
			}
			if resolved != "" {
				fmt.Fprintf(cmd.ErrOrStderr(), "FOUND_FROM_HTML: %s\n", resolved)
				sid = resolved
			}
		}
		if sid == "" {
			resolved, err := resolve.Current()
			if err != nil {
				exitErr(err)
			}
			sid = resolved
		}

		fmt.Fprintf(cmd.ErrOrStderr(), "SESSION: %s\n", sid)

		prompts, err := extract.Extract(sid)
		if err != nil {
			exitErr(err)
		}

		for i, p := range prompts {
			fmt.Printf("=== PROMPT %d | %s | %s ===\n", i+1, p.Timestamp, p.ID)
			fmt.Println(p.Text)
			fmt.Println()
		}
	},
}

func init() {
	rootCmd.AddCommand(scrapeCmd)
	scrapeCmd.Flags().StringVarP(&sessionID, "session", "s", "", "Explicit session ID (JCode or Codex thread UUID)")
	scrapeCmd.Flags().StringVarP(&outputFmt, "format", "f", "text", "Output format (text, json)")
}
