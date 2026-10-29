// Package resolve determines which harness session to scrape.
//
// Session ids are never guessed. They are derived from, in order:
//
//  1. an explicit id supplied by the caller
//  2. the JCODE_SESSION_ID environment variable
//  3. ids embedded in a state HTML file
//  4. the session whose working directory matches the current directory
//  5. the most recently updated session
package resolve

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// jcodeSessionRe matches a JCode session id, e.g. session_pig_1792638703385_34d0c212ece1d6b9.
var jcodeSessionRe = regexp.MustCompile(`session_[a-z]+_\d{13}_[0-9a-f]{16}`)

// codexUUIDRe matches a Codex thread id, e.g. 01a11ecd-9cb0-7003-acd4-2fa6e255169e.
var codexUUIDRe = regexp.MustCompile(`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`)

// FromHTML returns the candidate session ids embedded in an HTML file.
//
// A state HTML can reference several sessions (the JCode lane plus the Codex
// thread it audited), so every distinct candidate is returned, most frequent
// first. The caller decides which one to use.
func FromHTML(htmlPath string) ([]string, error) {
	content, err := os.ReadFile(htmlPath)
	if err != nil {
		return nil, err
	}
	return FromContent(string(content)), nil
}

// FromContent returns the candidate session ids found in HTML text.
func FromContent(s string) []string {
	counts := map[string]int{}
	order := []string{}

	record := func(id string) {
		if id == "" {
			return
		}
		if _, seen := counts[id]; !seen {
			order = append(order, id)
		}
		counts[id]++
	}

	for _, m := range jcodeSessionRe.FindAllString(s, -1) {
		record(m)
	}
	for _, m := range codexUUIDRe.FindAllString(s, -1) {
		record(m)
	}

	sort.SliceStable(order, func(a, b int) bool {
		return counts[order[a]] > counts[order[b]]
	})
	return order
}

// candidate is one session considered during resolution.
type candidate struct {
	id        string
	updatedAt string
	working   string
}

// Current returns the session id for the caller's environment.
//
// The JCODE_SESSION_ID environment variable wins, then a session whose working
// directory matches the current directory, then the most recently updated
// session.
func Current() (string, error) {
	if sid := strings.TrimSpace(os.Getenv("JCODE_SESSION_ID")); sid != "" {
		return sid, nil
	}

	dir, err := sessionsDir()
	if err != nil {
		return "", err
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", fmt.Errorf("cannot read %s: %w", dir, err)
	}

	cwd, cwdErr := os.Getwd()

	var candidates []candidate

	for _, e := range entries {
		if e.IsDir() || !strings.HasPrefix(e.Name(), "session_") || !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, e.Name()))
		if err != nil {
			continue
		}
		var sess struct {
			ID         string `json:"id"`
			WorkingDir string `json:"working_dir"`
			UpdatedAt  string `json:"updated_at"`
		}
		if err := json.Unmarshal(data, &sess); err != nil {
			continue
		}
		if sess.ID == "" {
			sess.ID = strings.TrimSuffix(e.Name(), ".json")
		}
		candidates = append(candidates, candidate{sess.ID, sess.UpdatedAt, sess.WorkingDir})
	}

	if len(candidates) == 0 {
		return "", fmt.Errorf("no jcode sessions found in %s", dir)
	}

	// Prefer a session running in the current directory.
	if cwdErr == nil {
		var matching []candidate
		for _, c := range candidates {
			if c.working == cwd {
				matching = append(matching, c)
			}
		}
		if len(matching) > 0 {
			sortByUpdatedDesc(matching)
			return matching[0].id, nil
		}
	}

	sortByUpdatedDesc(candidates)
	return candidates[0].id, nil
}

// sortByUpdatedDesc orders candidates by most-recently-updated first.
func sortByUpdatedDesc(candidates []candidate) {
	sort.SliceStable(candidates, func(a, b int) bool {
		return candidates[a].updatedAt > candidates[b].updatedAt
	})
}

// sessionsDir returns the directory holding JCode session files.
func sessionsDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot determine home directory: %w", err)
	}
	return filepath.Join(home, ".jcode", "sessions"), nil
}
