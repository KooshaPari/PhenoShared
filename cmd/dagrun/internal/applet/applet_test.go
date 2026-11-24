package applet

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"testing"
)

// schemaRelPath is where this repository keeps its copy of the shared applet
// contract, relative to the repo root.
const schemaRelPath = "docs/atlas/schemas/applet.schema.json"

// findSchema walks up from the package directory to the repo root. The path is
// searched rather than hard-coded because the same tree is built from a checkout
// and from a synced build directory, and a hard-coded depth silently skipped
// these tests once already.
func findSchema(t *testing.T) string {
	t.Helper()
	if root := os.Getenv("DAGRUN_SCHEMA_ROOT"); root != "" {
		p := filepath.Join(root, schemaRelPath)
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("cannot resolve the working directory: %v", err)
	}
	for i := 0; i < 6; i++ {
		p := filepath.Join(dir, schemaRelPath)
		if _, err := os.Stat(p); err == nil {
			return p
		}
		dir = filepath.Dir(dir)
	}
	// A missing schema is a FAILURE, not a skip: these two tests are the only
	// thing standing between this package and a manifest that violates its own
	// contract, and a skip would report that as success.
	t.Fatalf("applet schema not found: no %s within six levels of the package, and DAGRUN_SCHEMA_ROOT is unset", schemaRelPath)
	return ""
}

// loadSchema decodes the contract.
func loadSchema(t *testing.T) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(findSchema(t))
	if err != nil {
		t.Fatalf("cannot read the applet schema: %v", err)
	}
	var s map[string]any
	if err := json.Unmarshal(raw, &s); err != nil {
		t.Fatalf("schema is not JSON: %v", err)
	}
	return s
}

func TestContractConstantMatchesTheSchema(t *testing.T) {
	s := loadSchema(t)
	if got := s["$id"]; got != Contract {
		t.Fatalf("schema $id = %v, package Contract = %q: the manifest claims a contract the schema does not define", got, Contract)
	}
}

func TestManifestConformsToTheSchema(t *testing.T) {
	s := loadSchema(t)
	props, _ := s["properties"].(map[string]any)
	if len(props) == 0 {
		t.Fatal("schema has no properties")
	}
	schemaRequired, _ := s["required"].([]any)
	required := map[string]bool{}
	for _, r := range schemaRequired {
		name, _ := r.(string)
		required[name] = true
	}
	if len(required) == 0 {
		t.Fatal("schema declares nothing required")
	}
	// additionalProperties: false is the clause that makes /api/applet and this
	// package safe to split; assert it rather than assume it.
	if s["additionalProperties"] != false {
		t.Fatalf("schema allows additional properties; the split between manifest and discovery no longer holds")
	}

	raw, err := json.Marshal(Build("9.9.9-test"))
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatal(err)
	}

	for name := range required {
		if _, ok := got[name]; !ok {
			t.Errorf("manifest is missing required property %q", name)
		}
	}
	for name := range got {
		if _, ok := props[name]; !ok {
			t.Errorf("manifest carries %q, which the schema's additionalProperties:false rejects", name)
		}
	}
	for name, val := range got {
		spec, _ := props[name].(map[string]any)
		switch spec["type"] {
		case "string":
			str, ok := val.(string)
			if !ok {
				t.Errorf("%s is %T, want string", name, val)
				continue
			}
			if min, ok := spec["minLength"].(float64); ok && float64(len(str)) < min {
				t.Errorf("%s = %q is shorter than minLength %v", name, str, min)
			}
			if pat, ok := spec["pattern"].(string); ok && !regexp.MustCompile(pat).MatchString(str) {
				t.Errorf("%s = %q does not match the schema pattern %s", name, str, pat)
			}
		case "boolean":
			if _, ok := val.(bool); !ok {
				t.Errorf("%s is %T, want bool", name, val)
			}
		case "array":
			if _, ok := val.([]any); !ok {
				// A nil slice marshals to null, which the contract's "type":
				// "array" rejects. This is the failure mode worth catching.
				t.Errorf("%s is %T, want array (nil marshes to null)", name, val)
			}
		}
	}

	// The Go struct must expose exactly the schema's properties. DisallowUnknownFields
	// catches a field the schema does not define; the loop above catches the reverse.
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&strictManifest{}); err != nil {
		t.Fatalf("manifest does not decode into the strict struct: %v", err)
	}
	if got, want := strictFieldCount(), len(props); got != want {
		t.Fatalf("manifest struct has %d fields, schema has %d properties", got, want)
	}
}

// strictManifest mirrors Manifest field-for-field so a decoder can prove the
// document has no key the struct does not model.
type strictManifest Manifest

// strictFieldCount counts the struct's fields via its JSON contract, which is
// what the schema validates.
func strictFieldCount() int {
	raw, err := json.Marshal(Manifest{})
	if err != nil {
		return -1
	}
	var names map[string]json.RawMessage
	if err := json.Unmarshal(raw, &names); err != nil {
		return -1
	}
	return len(names)
}

func TestBuildReportsTheVersionItIsGiven(t *testing.T) {
	if got := Build("1.2.3").Version; got != "1.2.3" {
		t.Errorf("version = %q, want 1.2.3", got)
	}
	// An empty version would violate the contract's minLength 1, so it is
	// replaced rather than published.
	if got := Build("  ").Version; got != DefaultVersion {
		t.Errorf("blank version = %q, want %q", got, DefaultVersion)
	}
	if err := Build("").Validate(); err != nil {
		t.Errorf("manifest for an unversioned build does not validate: %v", err)
	}
}

func TestBuildIsNotSynthetic(t *testing.T) {
	if Build("1.0.0").Synthetic {
		t.Error("synthetic = true, but this is a real running instance")
	}
}

func TestValidateRejectsContractViolations(t *testing.T) {
	base := func() Manifest { return Build("1.0.0") }
	cases := map[string]func(m *Manifest){
		"nil capability list":    func(m *Manifest) { m.ProvidedCapabilities = nil },
		"nil ports":              func(m *Manifest) { m.Ports = nil },
		"nil children":           func(m *Manifest) { m.Children = nil },
		"empty version":          func(m *Manifest) { m.Version = "" },
		"empty federation":       func(m *Manifest) { m.FederationPolicy = "  " },
		"bad id":                 func(m *Manifest) { m.ID = "9bad" },
		"short subject":          func(m *Manifest) { m.SubjectID = "x" },
		"unknown surface":        func(m *Manifest) { m.Surfaces = []string{"hologram"} },
		"bad port direction":     func(m *Manifest) { m.Ports[0].Direction = "offers" },
		"bad port contract":      func(m *Manifest) { m.Ports[0].ContractID = "" },
		"empty port name":        func(m *Manifest) { m.Ports[0].Name = "" },
		"bad lifecycle id":       func(m *Manifest) { m.LifecycleContractID = "1bad" },
		"lifecycle id too short": func(m *Manifest) { m.LifecycleContractID = "x" },
	}
	names := make([]string, 0, len(cases))
	for name := range cases {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		m := base()
		cases[name](&m)
		if err := m.Validate(); err == nil {
			t.Errorf("%s: Validate accepted a manifest the contract rejects", name)
		}
	}
}

func TestFrameAncestorsDefaultsToSelf(t *testing.T) {
	got, err := FrameAncestors(nil)
	if err != nil {
		t.Fatal(err)
	}
	if got != SameOriginFrames {
		t.Fatalf("default = %q, want %q", got, SameOriginFrames)
	}
}

func TestFrameAncestorsKeepsSelfAndNamesTheConsumer(t *testing.T) {
	got, err := FrameAncestors([]string{"https://console.example:8443", "http://127.0.0.1:5173"})
	if err != nil {
		t.Fatal(err)
	}
	want := "'self' https://console.example:8443 http://127.0.0.1:5173"
	if got != want {
		t.Fatalf("policy = %q, want %q", got, want)
	}
	// A duplicate must not appear twice: frame-ancestors has no defined
	// duplicate semantics, and a longer header invites a reader to think it
	// grants more.
	again, err := FrameAncestors([]string{"https://console.example:8443", "https://console.example:8443/"})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Count(again, "console.example") != 1 {
		t.Fatalf("duplicate origin survived: %q", again)
	}
}

func TestFrameAncestorsRefusesAnythingButABareOrigin(t *testing.T) {
	for _, bad := range []string{
		"*",
		"https://*.example.com",
		"",
		"   ",
		"ftp://console.example",
		"console.example",
		"https://console.example/path",
		"https://user:pw@console.example",
		"https://console.example?q=1",
		"https://console.example#frag",
	} {
		if got, err := FrameAncestors([]string{bad}); err == nil {
			t.Errorf("%q was accepted as an origin, policy %q", bad, got)
		}
	}
}

func TestDiscoveryStatesTheReadOnlyFacts(t *testing.T) {
	d := NewDiscovery(DiscoveryOptions{Version: "1.2.3", Addr: "127.0.0.1:5555", Origin: "http://127.0.0.1:5555"})
	if d.Contract != Contract {
		t.Errorf("contract = %q, want %q", d.Contract, Contract)
	}
	if err := d.Applet.Validate(); err != nil {
		t.Errorf("embedded manifest does not validate: %v", err)
	}
	if !d.Mount.ReadOnly {
		t.Error("mount.read_only = false: an embeddable console surface must be an observer")
	}
	if d.Mount.Path != "/embed" {
		t.Errorf("mount.path = %q, want /embed", d.Mount.Path)
	}
	if d.Authority.Writes {
		t.Error("authority.writes = true: this surface has no write route")
	}
	if d.Authority.Owner != "dagrun" {
		t.Errorf("authority.owner = %q, want dagrun", d.Authority.Owner)
	}
	if d.Auth.Mode != "none-by-design" {
		t.Errorf("auth.mode = %q: the posture must be stated, not implied", d.Auth.Mode)
	}
	if d.Mount.FramePolicy != SameOriginFrames {
		t.Errorf("frame policy = %q, want the same-origin default", d.Mount.FramePolicy)
	}
	if d.Host.Origin != "http://127.0.0.1:5555" {
		t.Errorf("host.origin = %q", d.Host.Origin)
	}
	if !d.Host.Loopback {
		t.Error("host.loopback = false, but the server refuses any non-loopback address")
	}
	for _, r := range d.Routes {
		if !r.ReadOnly {
			t.Errorf("route %s is published as writable", r.Path)
		}
		if r.Method != "GET" {
			t.Errorf("route %s has method %q; this surface is a GET-only observer", r.Path, r.Method)
		}
	}
}

func TestRenderEmbedHasNoControls(t *testing.T) {
	html, err := RenderEmbed(Embed{
		Run:     "run-1",
		Version: "1.2.3",
		Nodes: []EmbedNode{
			{ID: "1", Title: "freeze scope", Kind: "INTENT", Status: "done"},
			{ID: "2", Title: "do the work", Kind: "IMPL", Status: "running", Owner: "jcode",
				Session: "abc123", Validated: true},
			{ID: "3", Title: "check", Status: "failed", LastError: "boom", Attempts: 2,
				Session: "def456", Validated: false, Artifacts: 2, Missing: 1},
		},
		Counts: []Count{{Status: "running", Count: 1}, {Status: "done", Count: 1}},
		Total:  3,
	})
	if err != nil {
		t.Fatal(err)
	}
	// No control surface. Every one of these would be a way to act on the run
	// from a second console.
	for _, banned := range []string{"<button", "<form", "<input", "<textarea", "<select", "contenteditable", "onclick"} {
		if strings.Contains(strings.ToLower(html), banned) {
			t.Errorf("embed contains %q; it must stay an observer", banned)
		}
	}
	for _, want := range []string{
		`data-applet="` + Contract + `"`,
		`data-read-only="true"`,
		`data-node="1"`, `data-node="2"`, `data-node="3"`,
		"run-1", "dagrun 1.2.3", "freeze scope", "abc123",
		"(unvalidated)", "boom", "2 attempts", "1 artifact(s) missing of 2",
		"read-only",
	} {
		if !strings.Contains(html, want) {
			t.Errorf("embed is missing %q", want)
		}
	}
	// A validated id is shown plainly; only an uncorroborated one is flagged.
	if strings.Contains(html, "abc123 (unvalidated)") {
		t.Error("a validated session id was reported as unvalidated")
	}
}

func TestRenderEmbedEscapesTitles(t *testing.T) {
	html, err := RenderEmbed(Embed{Run: "r", Nodes: []EmbedNode{{
		ID: "1", Title: `<script>alert("x")</script>`, Status: "pending",
	}}})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(html, `<script>alert`) {
		t.Fatal("a node title became markup")
	}
	if !strings.Contains(html, "&lt;script&gt;") {
		t.Fatal("the title was dropped rather than escaped")
	}
}

func TestRenderEmbedHandlesAnEmptyRun(t *testing.T) {
	html, err := RenderEmbed(Embed{Run: "r", Version: "dev"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(html, "no nodes in this run") {
		t.Fatal("an empty run should say so rather than render an empty table")
	}
	if !strings.Contains(html, `data-read-only="true"`) {
		t.Fatal("read-only marker missing even with no nodes")
	}
}
