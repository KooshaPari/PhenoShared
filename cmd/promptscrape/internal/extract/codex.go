package extract

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/klauspost/compress/zstd"
	_ "modernc.org/sqlite"
)

// codexSQLitePath returns the path of the Codex thread-history database.
func codexSQLitePath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	return filepath.Join(home, ".codex", "thread_history_1.sqlite")
}

// codexRolloutDir returns the directory holding Codex rollout transcripts.
func codexRolloutDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	return filepath.Join(home, ".codex", "sessions")
}

// extractCodexSQLite reads prompts for a thread from the thread-history database.
//
// The database is the authoritative store: it survives rollout-file pruning and
// carries both the stable item id and the creation timestamp.
func extractCodexSQLite(threadID string) ([]Prompt, error) {
	dbPath := codexSQLitePath()
	if dbPath == "" {
		return nil, fmt.Errorf("cannot determine home directory")
	}
	if _, err := os.Stat(dbPath); err != nil {
		return nil, fmt.Errorf("codex thread history not found at %s: %w", dbPath, err)
	}

	db, err := sql.Open("sqlite", "file:"+dbPath+"?mode=ro")
	if err != nil {
		return nil, fmt.Errorf("open codex thread history: %w", err)
	}
	defer db.Close()

	rows, err := db.Query(
		`SELECT item_id, created_at_ms, item_json
		 FROM thread_items
		 WHERE thread_id = ? AND item_type = 'userMessage'
		 ORDER BY rollout_ordinal`,
		threadID,
	)
	if err != nil {
		return nil, fmt.Errorf("query codex thread items: %w", err)
	}
	defer rows.Close()

	var prompts []Prompt
	for rows.Next() {
		var itemID string
		var createdAtMS int64
		var itemJSON string
		if err := rows.Scan(&itemID, &createdAtMS, &itemJSON); err != nil {
			continue
		}

		text := codexUserMessageText(itemJSON)
		if text == "" {
			continue
		}
		normalized, keep := normalizePrompt(text)
		if !keep {
			continue
		}

		// One stored message can pack several human prompts (Codex compresses a
		// resumed turn into a single item). Each gets its own sequence suffix so
		// the ids stay unique and traceable back to the source item.
		for i, promptText := range normalized {
			prompts = append(prompts, Prompt{
				ID:        codexPromptID(itemID, i, len(normalized)),
				Timestamp: epochMillisToRFC3339(createdAtMS),
				Text:      promptText,
			})
		}
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("scan codex thread items: %w", err)
	}
	return prompts, nil
}

// codexPromptID builds a unique, traceable id for one extracted prompt.
//
// A single stored Codex item can hold several human prompts. The item id is
// kept as the prefix so the prompt stays traceable back to its source, and a
// sequence suffix distinguishes the individual prompts.
func codexPromptID(itemID string, index, total int) string {
	if total <= 1 {
		return itemID
	}
	return fmt.Sprintf("%s#%d", itemID, index+1)
}

// codexUserMessageText pulls the first text block out of a stored userMessage.
func codexUserMessageText(itemJSON string) string {
	var item struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	if err := json.Unmarshal([]byte(itemJSON), &item); err != nil {
		return ""
	}
	for _, c := range item.Content {
		if c.Type == "text" && strings.TrimSpace(c.Text) != "" {
			return c.Text
		}
	}
	return ""
}

// epochMillisToRFC3339 converts a Codex millisecond epoch to an RFC3339 UTC stamp.
func epochMillisToRFC3339(ms int64) string {
	if ms <= 0 {
		return ""
	}
	return time.UnixMilli(ms).UTC().Format(time.RFC3339Nano)
}

// extractCodexRollout reads prompts from the on-disk rollout transcript.
//
// This is the fallback for threads whose sqlite history has been pruned or whose
// rollout file still holds items the projection has not yet consumed.
func extractCodexRollout(threadID string) ([]Prompt, error) {
	rollout, err := findCodexRollout(threadID)
	if err != nil {
		return nil, err
	}
	if rollout == "" {
		return nil, fmt.Errorf("no codex rollout file found for thread %s", threadID)
	}

	content, err := readCodexRollout(rollout)
	if err != nil {
		return nil, err
	}

	var prompts []Prompt
	seen := map[string]bool{}
	scanner := bufio.NewScanner(strings.NewReader(content))
	const maxLineSize = 8 * 1024 * 1024
	scanner.Buffer(make([]byte, 64*1024), maxLineSize)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var envelope struct {
			Type      string `json:"type"`
			Timestamp string `json:"timestamp"`
			Payload   struct {
				Type    string `json:"type"`
				Role    string `json:"role"`
				Content []struct {
					Type string `json:"type"`
					Text string `json:"text"`
				} `json:"content"`
				Metadata *struct {
					ContentItemKinds []string `json:"content_item_kinds"`
				} `json:"internal_chat_message_metadata_passthrough"`
			} `json:"payload"`
		}
		if err := json.Unmarshal(line, &envelope); err != nil {
			continue
		}
		if envelope.Type != "response_item" {
			continue
		}
		if envelope.Payload.Type != "message" || envelope.Payload.Role != "user" {
			continue
		}
		// The discriminator that separates a real typed prompt from injected context.
		if envelope.Payload.Metadata != nil {
			kinds := envelope.Payload.Metadata.ContentItemKinds
			if len(kinds) != 1 || kinds[0] != "user.text" {
				continue
			}
		}

		text := ""
		for _, c := range envelope.Payload.Content {
			if c.Type == "text" && strings.TrimSpace(c.Text) != "" {
				text = c.Text
				break
			}
		}
		if text == "" {
			continue
		}
		normalized, keep := normalizePrompt(text)
		if !keep {
			continue
		}

		id := fmt.Sprintf("%s#%d", threadID, len(prompts)+1)
		if seen[id] {
			continue
		}
		seen[id] = true
		for i, promptText := range normalized {
			prompts = append(prompts, Prompt{
				ID:        codexPromptID(id, i, len(normalized)),
				Timestamp: normalizeTimestamp(envelope.Timestamp),
				Text:      promptText,
			})
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("read codex rollout %s: %w", rollout, err)
	}
	return prompts, nil
}

// findCodexRollout locates the rollout transcript file for a thread.
func findCodexRollout(threadID string) (string, error) {
	dir := codexRolloutDir()
	if dir == "" {
		return "", fmt.Errorf("cannot determine home directory")
	}
	if _, err := os.Stat(dir); err != nil {
		return "", fmt.Errorf("codex sessions directory not found at %s: %w", dir, err)
	}

	var candidates []string
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() {
			return nil
		}
		if strings.Contains(info.Name(), threadID) {
			candidates = append(candidates, path)
		}
		return nil
	})
	if err != nil {
		return "", fmt.Errorf("walk codex sessions: %w", err)
	}
	if len(candidates) == 0 {
		return "", nil
	}
	sort.Strings(candidates)
	return candidates[len(candidates)-1], nil
}

// readCodexRollout reads a rollout file, transparently handling zstd compression.
func readCodexRollout(path string) (string, error) {
	if !strings.HasSuffix(path, ".zst") {
		data, err := os.ReadFile(path)
		if err != nil {
			return "", fmt.Errorf("read %s: %w", path, err)
		}
		return string(data), nil
	}

	f, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	dec, err := zstd.NewReader(f)
	if err != nil {
		// Fall back to the system zstd binary.
		cmd := exec.Command("zstd", "-d", "-c", path)
		out, cmdErr := cmd.Output()
		if cmdErr != nil {
			return "", fmt.Errorf("decompress %s: %w", path, cmdErr)
		}
		return string(out), nil
	}
	defer dec.Close()

	data, err := io.ReadAll(dec)
	if err != nil {
		return "", fmt.Errorf("decompress %s: %w", path, err)
	}
	return string(data), nil
}

// normalizeTimestamp converts a Codex ISO timestamp to RFC3339 UTC.
func normalizeTimestamp(ts string) string {
	if ts == "" {
		return ""
	}
	parsed, err := time.Parse(time.RFC3339Nano, ts)
	if err != nil {
		return ts
	}
	return parsed.UTC().Format(time.RFC3339Nano)
}
