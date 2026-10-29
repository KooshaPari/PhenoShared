package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/KooshaPari/PhenoShared/cmd/promptscrape/internal/extract"
	"github.com/KooshaPari/PhenoShared/cmd/promptscrape/internal/resolve"
	"github.com/spf13/cobra"
)

var (
	htmlPath   string
	sessionID  string
	outputFmt  string
	showSource bool
)

var scrapeCmd = &cobra.Command{
	Use:   "scrape [html-path]",
	Short: "Scrape the prompt timeline from a JCode or Codex session",
	Long: `Scrape the full user prompt timeline from a JCode or Codex session.

The session id is derived automatically:
  1. --session flag, or the JCODE_SESSION_ID environment variable
  2. a session id embedded in the given HTML file
  3. the session whose working directory matches the current directory
  4. the most recently updated session

Only real human prompts are returned. Harness-injected context (system
reminders, environment context, permissions, AGENTS.md) and tool results are
filtered out.`,
	Example: `  promptscrape scrape
  promptscrape scrape ~/Exports/lane-walkthrough.html
  promptscrape scrape --session session_pig_1792638703385_34d0c212ece1d6b9
  promptscrape scrape --session 019dd872-83de-76b1-a635-7bce3b0f3a54 --format json`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) > 0 {
			htmlPath = args[0]
		}

		sid, err := resolveSessionID(cmd, htmlPath, sessionID)
		if err != nil {
			return err
		}

		timeline, err := extract.Extract(sid)
		if err != nil {
			return err
		}

		fmt.Fprintf(cmd.ErrOrStderr(), "SESSION: %s (source: %s, prompts: %d)\n",
			timeline.SessionID, timeline.Source, len(timeline.Prompts))

		switch outputFmt {
		case "json":
			return writeJSON(cmd, timeline)
		case "text", "":
			writeText(cmd, timeline)
			return nil
		default:
			return fmt.Errorf("unknown format %q (want text or json)", outputFmt)
		}
	},
}

// resolveSessionID determines which session to scrape.
//
// A state HTML can reference more than one session, so every candidate found
// in the file is tried in turn and the first one that actually yields prompts
// wins. That way a file naming both a JCode lane and the Codex thread it
// audited resolves to whichever session still has data.
func resolveSessionID(cmd *cobra.Command, htmlPath, explicit string) (string, error) {
	if explicit != "" {
		return explicit, nil
	}

	if htmlPath != "" {
		candidates, err := resolve.FromHTML(htmlPath)
		if err != nil {
			return "", fmt.Errorf("read %s: %w", htmlPath, err)
		}
		if len(candidates) == 0 {
			fmt.Fprintf(cmd.ErrOrStderr(), "NO_SESSION_IN_HTML: %s\n", htmlPath)
		}
		for _, candidate := range candidates {
			prompts, err := extract.Extract(candidate)
			if err == nil && len(prompts.Prompts) > 0 {
				fmt.Fprintf(cmd.ErrOrStderr(), "FOUND_FROM_HTML: %s\n", candidate)
				return candidate, nil
			}
		}
		if len(candidates) > 0 {
			fmt.Fprintf(cmd.ErrOrStderr(), "NO_PROMPTS_IN_HTML_CANDIDATES: %v\n", candidates)
		}
	}

	resolved, err := resolve.Current()
	if err != nil {
		return "", fmt.Errorf("could not resolve a session: %w", err)
	}
	return resolved, nil
}

// writeText prints the human-readable timeline.
func writeText(cmd *cobra.Command, tl *extract.Timeline) {
	for i, p := range tl.Prompts {
		fmt.Fprintf(cmd.OutOrStdout(), "=== PROMPT %d | %s | %s ===\n", i+1, p.Timestamp, p.ID)
		fmt.Fprintln(cmd.OutOrStdout(), p.Text)
		fmt.Fprintln(cmd.OutOrStdout())
	}
}

// writeJSON prints the machine-readable timeline for downstream curation tools.
func writeJSON(cmd *cobra.Command, tl *extract.Timeline) error {
	encoder := json.NewEncoder(cmd.OutOrStdout())
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(tl); err != nil {
		return fmt.Errorf("encode json: %w", err)
	}
	return nil
}

func init() {
	rootCmd.AddCommand(scrapeCmd)
	scrapeCmd.Flags().StringVarP(&sessionID, "session", "s", "", "Explicit session id (JCode id or Codex thread UUID)")
	scrapeCmd.Flags().StringVarP(&outputFmt, "format", "f", "text", "Output format: text or json")
	scrapeCmd.Flags().BoolVar(&showSource, "show-source", false, "Print the resolved session id and source to stdout")
}
