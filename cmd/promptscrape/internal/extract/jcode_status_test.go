package extract

import (
	"encoding/json"
	"testing"
)

// TestJCodeStatusUnmarshal guards against the regression where a crashed session's
// tagged-enum status made the whole snapshot unreadable.
func TestJCodeStatusUnmarshal(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"plain string", `"Running"`, "Running"},
		{"tagged enum with message", `{"Crashed":{"message":"Client disconnected while processing"}}`, "Crashed: Client disconnected while processing"},
		{"tagged enum without message", `{"Idle":{}}`, "Idle"},
		{"null", `null`, ""},
		{"empty bytes", ``, ""},
		{"garbage", `42`, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var got jcodeStatus
			if err := got.UnmarshalJSON([]byte(tc.in)); err != nil {
				t.Fatalf("UnmarshalJSON(%q) returned error: %v", tc.in, err)
			}
			if string(got) != tc.want {
				t.Fatalf("UnmarshalJSON(%q) = %q, want %q", tc.in, string(got), tc.want)
			}
		})
	}
}

// TestJCodeSessionFileTaggedStatus is the end-to-end shape check: the live crashed
// snapshot must decode instead of aborting.
func TestJCodeSessionFileTaggedStatus(t *testing.T) {
	body := `{"id":"session_snake_1789889071967_eadc10bc01a51627","working_dir":"/tmp","status":{"Crashed":{"message":"Client disconnected while processing"}},"messages":[]}`
	var f jcodeSessionFile
	if err := json.Unmarshal([]byte(body), &f); err != nil {
		t.Fatalf("session snapshot with tagged-enum status must decode, got: %v", err)
	}
	if string(f.Status) != "Crashed: Client disconnected while processing" {
		t.Fatalf("status = %q", string(f.Status))
	}
}
