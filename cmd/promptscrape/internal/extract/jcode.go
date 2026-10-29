package extract

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func extractJCode(sessionID string) ([]Prompt, error) {
	home, _ := os.UserHomeDir()
	sessionsDir := filepath.Join(home, ".jcode", "sessions")
	
	jsonPath := filepath.Join(sessionsDir, sessionID+".json")
	journalPath := filepath.Join(sessionsDir, sessionID+".journal.jsonl")
	
	type contentBlock struct {
		Type string `json:"type"`
		Text string `json:"text"`
	}
	type message struct {
		ID           string         `json:"id"`
		Role         string         `json:"role"`
		Content      []contentBlock `json:"content"`
		DisplayRole  string         `json:"display_role"`
		Timestamp    string         `json:"timestamp"`
	}
	
	var messages []message
	seen := map[string]bool{}
	
	// Load from JSON
	if data, err := os.ReadFile(jsonPath); err == nil {
		var sess struct {
			Messages []message `json:"messages"`
		}
		if json.Unmarshal(data, &sess) == nil {
			for _, m := range sess.Messages {
				messages = append(messages, m)
				seen[m.ID] = true
			}
		}
	}
	
	// Load from journal
	if f, err := os.Open(journalPath); err == nil {
		scanner := bufio.NewScanner(f)
		// Increase buffer size for large lines
		const maxTokenSize = 1024 * 1024
		scanner.Buffer(make([]byte, maxTokenSize), maxTokenSize)
		scanner.Split(bufio.ScanLines)
		
		for scanner.Scan() {
			var entry struct {
				AppendMessages []message `json:"append_messages"`
			}
			if json.Unmarshal(scanner.Bytes(), &entry) == nil {
				for _, m := range entry.AppendMessages {
					if !seen[m.ID] {
						messages = append(messages, m)
						seen[m.ID] = true
					}
				}
			}
		}
		f.Close()
	}
	
	// Sort by timestamp
	sort.Slice(messages, func(i, j int) bool {
		return messages[i].Timestamp < messages[j].Timestamp
	})
	
	var prompts []Prompt
	for _, m := range messages {
		if m.Role != "user" {
			continue
		}
		if m.DisplayRole == "system" {
			continue
		}
		for _, c := range m.Content {
			if c.Type == "text" {
				text := c.Text
				if strings.HasPrefix(text, "<system-reminder>") {
					continue
				}
				prompts = append(prompts, Prompt{
					ID:        m.ID,
					Timestamp: m.Timestamp,
					Text:      text,
				})
				break
			}
		}
	}
	
	return prompts, nil
}
