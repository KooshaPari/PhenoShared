package server

import (
	"encoding/json"
	"net/http"
	"strings"
	"testing"
)

// A launcher asking for a route dagrun never had must be told so. Answering 200
// text/html meant a program parsed the viewer as data, or read a silent wrong
// answer as a working call; both happened during launcher work.
func TestUnknownMachinePathAnswers404JSON(t *testing.T) {
	s := newServer(t, fixture(t))
	for _, path := range []string{"/api/servers", "/api/instances", "/api/no-such-thing", "/.well-known/other.json"} {
		code, body := get(t, s, path)
		if code != http.StatusNotFound {
			t.Errorf("%s: status = %d, want 404", path, code)
			continue
		}
		if !strings.HasPrefix(strings.TrimSpace(body), "{") {
			t.Errorf("%s: body is not JSON: %.60q", path, body)
			continue
		}
		var doc map[string]any
		if err := json.Unmarshal([]byte(body), &doc); err != nil {
			t.Errorf("%s: not JSON: %v", path, err)
			continue
		}
		if doc["error"] != "no such route" {
			t.Errorf("%s: error = %v, want \"no such route\"", path, doc["error"])
		}
		// The path is echoed so a caller can see WHICH route it got wrong; a
		// quoted field, so a hostile path cannot break the document.
		if doc["path"] != path {
			t.Errorf("%s: path = %v, want %s", path, doc["path"], path)
		}
	}
}

// The refusal is scoped to machine namespaces. A browser asking for an unknown
// page still gets the viewer, because a 404 page is not what that request meant.
func TestUnknownPagePathStillRendersTheViewer(t *testing.T) {
	s := newServer(t, fixture(t))
	for _, path := range []string{"/", "/index.html", "/nodes/2", "/anything-else"} {
		code, body := get(t, s, path)
		if code != http.StatusOK {
			t.Errorf("%s: status = %d, want 200", path, code)
			continue
		}
		if !strings.Contains(body, "<html") {
			t.Errorf("%s: not the viewer: %.60q", path, body)
		}
	}
}

// The refusal must not swallow the routes that do exist, including the two in
// the .well-known namespace and the one with a trailing path segment.
func TestKnownRoutesAreNotSwallowedByTheFallback(t *testing.T) {
	s := newServer(t, fixture(t))
	for _, path := range []string{
		"/api/health", "/api/plan", "/api/status", "/api/agents", "/api/query",
		"/api/applet", "/api/nodes/2", "/.well-known/applet.json", "/embed",
	} {
		code, _ := get(t, s, path)
		if code == http.StatusNotFound {
			t.Errorf("%s: status = 404, want the registered handler", path)
		}
	}
}

func TestMachinePathClassification(t *testing.T) {
	cases := map[string]bool{
		"/api/servers":             true,
		"/api/":                    true,
		"/.well-known/applet.json": true,
		"/api":                     false, // no trailing slash: a page path, not a namespace
		"/":                        false,
		"/embed":                   false,
		"/nodes/2":                 false,
		"/apiary/something":        false, // prefix must be the whole segment
	}
	for path, want := range cases {
		if got := isMachinePath(path); got != want {
			t.Errorf("isMachinePath(%q) = %v, want %v", path, got, want)
		}
	}
}
