package extract

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// jcodeMessage is one message in a JCode session.
//
// The on-disk shape is identical in the session snapshot and the journal:
//   - id:         stable message id, e.g. message_1793249328054_4234567178120536763
//   - role:       "user" or "assistant"
//   - display_role: optional marker; "system" means harness-injected
//   - content:    ordered blocks; "text" is human input, "tool_result" is tool output
//   - timestamp:  RFC3339 with microsecond precision, UTC
type jcodeMessage struct {
	ID          string            `json:"id"`
	Role        string            `json:"role"`
	DisplayRole string            `json:"display_role"`
	Timestamp   string            `json:"timestamp"`
	Content     []jcodeContentBlk `json:"content"`
}

// jcodeContentBlk is one content block within a message.
type jcodeContentBlk struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// jcodeSessionFile is the session snapshot written by the harness.
type jcodeSessionFile struct {
	ID         string         `json:"id"`
	WorkingDir string         `json:"working_dir"`
	Status     string         `json:"status"`
	UpdatedAt  string         `json:"updated_at"`
	Messages   []jcodeMessage `json:"messages"`
}

// jcodeJournalEntry is one line of the append-only journal.
type jcodeJournalEntry struct {
	Meta           *jcodeJournalMeta `json:"meta"`
	AppendMessages []jcodeMessage    `json:"append_messages"`
}

// jcodeJournalMeta carries the mutable session metadata.
type jcodeJournalMeta struct {
	WorkingDir string `json:"working_dir"`
	Status     string `json:"status"`
	UpdatedAt  string `json:"updated_at"`
	Title      string `json:"title"`
}

// jcodeSessionsDir returns the directory holding JCode session files.
func jcodeSessionsDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot determine home directory: %w", err)
	}
	return filepath.Join(home, ".jcode", "sessions"), nil
}

// extractJCode reads the prompt timeline for a JCode session.
//
// Two files are merged:
//   - <id>.json         the harness snapshot, authoritative for messages it contains
//   - <id>.journal.jsonl an append-only log of messages written after the snapshot
//
// Messages are deduplicated by id (the journal wins on conflict, since it is
// written later and carries the same shape) and ordered by timestamp.
func extractJCode(sessionID string) ([]Prompt, error) {
	dir, err := jcodeSessionsDir()
	if err != nil {
		return nil, err
	}

	jsonPath := filepath.Join(dir, sessionID+".json")
	journalPath := filepath.Join(dir, sessionID+".journal.jsonl")

	messages := map[string]jcodeMessage{}
	order := []string{}

	add := func(m jcodeMessage) {
		if m.ID == "" {
			return
		}
		if _, exists := messages[m.ID]; !exists {
			order = append(order, m.ID)
		}
		messages[m.ID] = m
	}

	// Snapshot first.
	if data, err := os.ReadFile(jsonPath); err == nil {
		var sess jcodeSessionFile
		if err := json.Unmarshal(data, &sess); err != nil {
			return nil, fmt.Errorf("parse jcode session %s: %w", jsonPath, err)
		}
		for _, m := range sess.Messages {
			add(m)
		}
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("read jcode session %s: %w", jsonPath, err)
	}

	// Journal appends after it.
	if err := mergeJCodeJournal(journalPath, add); err != nil {
		return nil, err
	}

	if len(messages) == 0 {
		return nil, fmt.Errorf("no messages found for jcode session %s", sessionID)
	}

	// Sort by timestamp, then by id so the order is stable for equal stamps.
	sort.SliceStable(order, func(a, b int) bool {
		ma, mb := messages[order[a]], messages[order[b]]
		if ma.Timestamp != mb.Timestamp {
			return ma.Timestamp < mb.Timestamp
		}
		return ma.ID < mb.ID
	})

	var prompts []Prompt
	for _, id := range order {
		m := messages[id]
		if m.Role != "user" {
			continue
		}
		// display_role marks harness-injected turns.
		if m.DisplayRole == "system" || m.DisplayRole == "background_task" {
			continue
		}
		text := jcodeUserText(m)
		if text == "" {
			continue
		}
		normalized, keep := normalizePrompt(text)
		if !keep {
			continue
		}
		for i, promptText := range normalized {
			prompts = append(prompts, Prompt{
				ID:        jcodePromptID(m.ID, i, len(normalized)),
				Timestamp: m.Timestamp,
				Text:      promptText,
			})
		}
	}
	return prompts, nil
}

// jcodePromptID builds a unique, traceable id for one extracted prompt.
//
// A single stored message can hold several human prompts when the harness
// replays a rendered turn. The message id is kept as the prefix so the prompt
// stays traceable back to its source, and a sequence suffix distinguishes the
// individual prompts.
func jcodePromptID(messageID string, index, total int) string {
	if total <= 1 {
		return messageID
	}
	return fmt.Sprintf("%s#%d", messageID, index+1)
}

// mergeJCodeJournal reads the append-only journal and feeds its messages to add.
func mergeJCodeJournal(path string, add func(jcodeMessage)) error {
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("open jcode journal %s: %w", path, err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	const maxLineSize = 16 * 1024 * 1024
	scanner.Buffer(make([]byte, 64*1024), maxLineSize)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var entry jcodeJournalEntry
		if err := json.Unmarshal(line, &entry); err != nil {
			continue
		}
		for _, m := range entry.AppendMessages {
			add(m)
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("read jcode journal %s: %w", path, err)
	}
	return nil
}

// jcodeUserText extracts the human-authored text from a user message.
//
// A user message may carry several content blocks. Tool results arrive in the
// same role, so only "text" blocks count, and only the first one: JCode puts the
// human input first and the tool output after it.
func jcodeUserText(m jcodeMessage) string {
	for _, c := range m.Content {
		if c.Type != "text" {
			continue
		}
		text := strings.TrimSpace(c.Text)
		if text == "" {
			continue
		}
		return text
	}
	return ""
}
