package harness

import (
	"bytes"
	"encoding/json"
	"strings"
)

// ParseSessionID extracts the child harness's own session identifier from its
// output.
//
// This is the missing half of node identity. dagrun already keeps the harness
// binary name and the provider/model the plan asked for, but a finished node
// could not say WHICH session it ran: the id is printed by the child and was
// thrown away with the rest of the log tail. A console that wants to bind a
// graph node to the agent card that actually executed it needs that id.
//
// The parse is deliberately narrow. Only four keys name a session in the
// harness exit objects observed on this host (jcode/kcode, codex), and only a
// non-empty, whitespace-free, bounded string is accepted. Anything else returns
// ("", ""): a wrong id is worse than no id, because it would validate against
// nothing and silently be reported as a different agent's card.
//
// source reports which key matched, so the record can say how it learned the
// id rather than presenting it as authoritative.
func ParseSessionID(data []byte) (id, source string) {
	// Multi-line JSONL is the normal shape for jcode run --json and
	// codex exec --json, so walk it and keep the LAST object that names a
	// session. The last one is the most recent view of the same session.
	var lastID, lastSource string
	for _, line := range bytes.Split(data, []byte("\n")) {
		line = bytes.TrimSpace(line)
		if len(line) == 0 || line[0] != '{' {
			continue
		}
		gotID, gotSource := sessionFromObject(line)
		if gotID != "" {
			lastID, lastSource = gotID, gotSource
		}
	}
	if lastID != "" {
		return lastID, lastSource
	}

	// A single pretty-printed object (or one object with no trailing newline).
	trimmed := bytes.TrimSpace(data)
	if len(trimmed) > 0 && trimmed[0] == '{' {
		return sessionFromObject(trimmed)
	}
	return "", ""
}

// sessionKeys are the only object keys treated as a session id, in the order
// they are trusted when an object carries more than one.
//
// "id" is deliberately absent: it appears on artifacts, spans and nodes, and
// reading it as a session id would fabricate identity.
var sessionKeys = []string{"session_id", "sessionId", "thread_id", "conversation_id"}

func sessionFromObject(raw []byte) (id, source string) {
	var obj map[string]any
	if err := json.Unmarshal(raw, &obj); err != nil {
		return "", ""
	}
	for _, key := range sessionKeys {
		v, ok := obj[key]
		if !ok {
			continue
		}
		s, ok := v.(string)
		if !ok || !plausibleSessionID(s) {
			continue
		}
		return s, "stdout:" + key
	}
	// Some harnesses nest the id under an info/event wrapper.
	for _, wrap := range []string{"info", "event", "session"} {
		inner, ok := obj[wrap].(map[string]any)
		if !ok {
			continue
		}
		for _, key := range sessionKeys {
			v, ok := inner[key]
			if !ok {
				continue
			}
			s, ok := v.(string)
			if !ok || !plausibleSessionID(s) {
				continue
			}
			return s, "stdout:" + wrap + "." + key
		}
	}
	return "", ""
}

// plausibleSessionID rejects values that cannot be a session id: empty,
// whitespace, path separators, or longer than any id this host produces.
func plausibleSessionID(s string) bool {
	if s == "" || len(s) > 200 {
		return false
	}
	if strings.ContainsAny(s, " \t\r\n/\\") {
		return false
	}
	return true
}
