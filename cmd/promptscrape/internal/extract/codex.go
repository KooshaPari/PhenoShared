package extract

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/klauspost/compress/zstd"
	_ "github.com/mattn/go-sqlite3"
)

func extractCodexSQLite(threadID string) ([]Prompt, error) {
	home, _ := os.UserHomeDir()
	dbPath := filepath.Join(home, ".codex", "thread_history_1.sqlite")
	
	db, err := sql.Open("sqlite3", "file:"+dbPath+"?mode=ro")
	if err != nil {
		return nil, err
	}
	defer db.Close()
	
	rows, err := db.Query("SELECT turn_id, rollout_ordinal, item_json FROM thread_items WHERE thread_id = ? AND item_type = 'userMessage' ORDER BY rollout_ordinal", threadID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var prompts []Prompt
	for rows.Next() {
		var turnID string
		var ordinal int
		var itemJSON string
		if err := rows.Scan(&turnID, &ordinal, &itemJSON); err != nil {
			continue
		}
		var item map[string]interface{}
		if json.Unmarshal([]byte(itemJSON), &item) != nil {
			continue
		}
		content, ok := item["content"].([]interface{})
		if !ok {
			continue
		}
		for _, c := range content {
			if cm, ok := c.(map[string]interface{}); ok {
				if text, ok := cm["text"].(string); ok {
					if strings.HasPrefix(text, "<environment_context>") || strings.HasPrefix(text, "<permissions instructions>") {
						continue
					}
					if strings.HasPrefix(strings.TrimSpace(text), "<|") {
						continue
					}
					if len(text) < 5 {
						continue
					}
					id := turnID
					if id == "" {
						id = threadID + ":" + string(rune(ordinal))
					}
					prompts = append(prompts, Prompt{
						ID:        id,
						Timestamp: "",
						Text:      text,
					})
					break
				}
			}
		}
	}
	return prompts, nil
}

func extractCodexRollout(threadID string) ([]Prompt, error) {
	home, _ := os.UserHomeDir()
	sessionsDir := filepath.Join(home, ".codex", "sessions")
	
	var candidates []string
	filepath.Walk(sessionsDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if strings.Contains(info.Name(), threadID) {
			candidates = append(candidates, path)
		}
		return nil
	})
	
	if len(candidates) == 0 {
		return nil, nil
	}
	sort.Strings(candidates)
	rollout := candidates[len(candidates)-1]
	
	var content string
	if strings.HasSuffix(rollout, ".zst") {
		f, err := os.Open(rollout)
		if err != nil {
			return nil, err
		}
		dec, err := zstd.NewReader(f)
		if err != nil {
			// try system zstd
			f.Close()
			cmd := exec.Command("zstd", "-d", "-c", rollout)
			out, err := cmd.Output()
			if err != nil {
				return nil, err
			}
			content = string(out)
		} else {
			data, err := io.ReadAll(dec)
			dec.Close()
			f.Close()
			if err != nil {
				return nil, err
			}
			content = string(data)
		}
	} else {
		data, err := os.ReadFile(rollout)
		if err != nil {
			return nil, err
		}
		content = string(data)
	}
	
	var prompts []Prompt
	scanner := bufio.NewScanner(strings.NewReader(content))
	const maxTokenSize = 1024 * 1024
	scanner.Buffer(make([]byte, maxTokenSize), maxTokenSize)
	scanner.Split(bufio.ScanLines)
	
	for scanner.Scan() {
		var obj map[string]interface{}
		if json.Unmarshal(scanner.Bytes(), &obj) != nil {
			continue
		}
		if obj["type"] != "response_item" {
			continue
		}
		payload, ok := obj["payload"].(map[string]interface{})
		if !ok {
			continue
		}
		if payload["type"] != "message" || payload["role"] != "user" {
			continue
		}
		// Check discriminator
		if meta, ok := payload["internal_chat_message_metadata_passthrough"].(map[string]interface{}); ok {
			if kinds, ok := meta["content_item_kinds"].([]interface{}); ok {
				if len(kinds) != 1 || kinds[0] != "user.text" {
					continue
				}
			}
		}
		contentArr, ok := payload["content"].([]interface{})
		if !ok {
			continue
		}
		for _, c := range contentArr {
			if cm, ok := c.(map[string]interface{}); ok {
				if text, ok := cm["text"].(string); ok {
					if strings.HasPrefix(text, "<environment_context>") || strings.HasPrefix(text, "<permissions instructions>") {
						continue
					}
					if strings.HasPrefix(strings.TrimSpace(text), "<|") {
						continue
					}
					prompts = append(prompts, Prompt{
						ID:        threadID,
						Timestamp: getString(obj, "timestamp"),
						Text:      text,
					})
					break
				}
			}
		}
	}
	return prompts, nil
}

func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}
