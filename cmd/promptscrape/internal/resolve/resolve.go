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

var sessionRe = regexp.MustCompile(`(session_[a-z]+_\d{13}_[0-9a-f]{16})`)
var codexRe = regexp.MustCompile(`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`)

func FromHTML(htmlPath string) (string, error) {
	content, err := os.ReadFile(htmlPath)
	if err != nil {
		return "", err
	}
	s := string(content)
	
	// Try JCode sessions first
	matches := sessionRe.FindAllString(s, -1)
	if len(matches) > 0 {
		// Count occurrences
		count := map[string]int{}
		for _, m := range matches {
			count[m]++
		}
		// Return most common
		type pair struct {
			k string
			v int
		}
		var pairs []pair
		for k, v := range count {
			pairs = append(pairs, pair{k, v})
		}
		sort.Slice(pairs, func(i, j int) bool { return pairs[i].v > pairs[j].v })
		return pairs[0].k, nil
	}
	
	// Try Codex UUIDs
	matches2 := codexRe.FindAllString(s, -1)
	if len(matches2) > 0 {
		count := map[string]int{}
		for _, m := range matches2 {
			count[m]++
		}
		type pair struct {
			k string
			v int
		}
		var pairs []pair
		for k, v := range count {
			pairs = append(pairs, pair{k, v})
		}
		sort.Slice(pairs, func(i, j int) bool { return pairs[i].v > pairs[j].v })
		return pairs[0].k, nil
	}
	
	return "", nil
}

func Current() (string, error) {
	// 1. env var
	if sid := os.Getenv("JCODE_SESSION_ID"); sid != "" {
		return sid, nil
	}
	
	home, _ := os.UserHomeDir()
	sessionsDir := filepath.Join(home, ".jcode", "sessions")
	
	// 2. try cwd match
	cwd, _ := os.Getwd()
	type candidate struct {
		id        string
		updatedAt string
	}
	var candidates []candidate
	
	entries, err := os.ReadDir(sessionsDir)
	if err != nil {
		return "", err
	}
	
	for _, e := range entries {
		if e.IsDir() || !strings.HasPrefix(e.Name(), "session_") || !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		if strings.HasSuffix(e.Name(), ".journal.jsonl") || strings.HasSuffix(e.Name(), ".bak") {
			continue
		}
		path := filepath.Join(sessionsDir, e.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var sess struct {
			ID         string `json:"id"`
			WorkingDir string `json:"working_dir"`
			Status     string `json:"status"`
			UpdatedAt  string `json:"updated_at"`
		}
		if err := json.Unmarshal(data, &sess); err != nil {
			continue
		}
		if sess.WorkingDir == cwd && (sess.Status == "Active" || sess.Status == "Idle" || sess.Status == "") {
			candidates = append(candidates, candidate{sess.ID, sess.UpdatedAt})
		}
	}
	
	if len(candidates) > 0 {
		sort.Slice(candidates, func(i, j int) bool { return candidates[i].updatedAt > candidates[j].updatedAt })
		return candidates[0].id, nil
	}
	
	// 3. most recent
	candidates = nil
	for _, e := range entries {
		if e.IsDir() || !strings.HasPrefix(e.Name(), "session_") || !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		if strings.HasSuffix(e.Name(), ".journal.jsonl") || strings.HasSuffix(e.Name(), ".bak") {
			continue
		}
		path := filepath.Join(sessionsDir, e.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var sess struct {
			ID        string `json:"id"`
			UpdatedAt string `json:"updated_at"`
		}
		if err := json.Unmarshal(data, &sess); err != nil {
			continue
		}
		candidates = append(candidates, candidate{sess.ID, sess.UpdatedAt})
	}
	
	if len(candidates) > 0 {
		sort.Slice(candidates, func(i, j int) bool { return candidates[i].updatedAt > candidates[j].updatedAt })
		return candidates[0].id, nil
	}
	
	return "", fmt.Errorf("no session found")
}
