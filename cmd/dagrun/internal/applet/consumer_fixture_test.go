package applet

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The workboard is a consumer that reads this registry but does not own it, and a
// reader's bugs are invisible from the writer's side: two rows for one server, an id
// shaped like a sentence, and a directory of corrupt files rendered as "no servers"
// all look fine to whoever wrote the files. These tests pin the reader against bytes
// captured from a live `dagrun serve`, so a change that would make a consumer render
// nonsense fails here instead of in a workboard.
//
// The fixture in testdata/workboard is not generated. Its expected.json records what
// each record is and why it matters, and every expectation was measured against this
// reader rather than reasoned about.

// consumerCase is one row of testdata/workboard/expected.json.
type consumerCase struct {
	File                 string `json:"file"`
	InputState           string `json:"input_state"`
	ListedWithoutVerify  bool   `json:"listed_without_verify"`
	ListedWithVerify     bool   `json:"listed_with_verify"`
	VerifyOutcome        string `json:"verify_outcome"`
	ExpectedAdapterState string `json:"expected_adapter_state"`
	Trap                 string `json:"trap"`
}

type consumerFixture struct {
	Fixture       string         `json:"fixture"`
	CapturedAtUTC string         `json:"captured_at_utc"`
	RegistryFmt   string         `json:"registry_format"`
	Cases         []consumerCase `json:"cases"`
	ProcessCases  []struct {
		Case                 string `json:"case"`
		Observed             string `json:"observed"`
		ExpectedAdapterState string `json:"expected_adapter_state"`
		Trap                 string `json:"trap"`
	} `json:"process_cases"`
}

func loadConsumerFixture(t *testing.T) consumerFixture {
	t.Helper()
	body, err := os.ReadFile(filepath.Join("testdata", "workboard", "expected.json"))
	if err != nil {
		t.Fatalf("read fixture expectations: %v", err)
	}
	var f consumerFixture
	if err := json.Unmarshal(body, &f); err != nil {
		t.Fatalf("parse fixture expectations: %v", err)
	}
	if len(f.Cases) == 0 {
		t.Fatal("fixture has no cases; the expectations file is the point of the fixture")
	}
	return f
}

// TestConsumerFixtureMatchesMeasuredExpectations replays every record through the
// reader and compares the outcome with what was measured when the fixture was
// captured. A row that appears where the fixture says "error", or a file that
// disappears from both lists, is a change in the reader's contract with consumers.
func TestConsumerFixtureMatchesMeasuredExpectations(t *testing.T) {
	fx := loadConsumerFixture(t)

	listed := map[string]bool{}
	var failed []string
	for _, dir := range []string{"live", "mixed"} {
		instances, errs := ReadInstances(filepath.Join("testdata", "workboard", dir))
		for _, inst := range instances {
			listed[inst.ID] = true
		}
		for _, err := range errs {
			failed = append(failed, err.Error())
		}
	}

	for _, c := range fx.Cases {
		name := filepath.Base(c.File)
		switch {
		case c.ExpectedAdapterState == "IGNORED":
			if mentioned(failed, name) {
				t.Errorf("%s: a non-JSON file must be ignored silently, but it was reported as an error (%s)", c.File, c.Trap)
			}
		case c.ListedWithoutVerify:
			if !listed[c.ExpectedAdapterState] && !listed[duplicateID] {
				t.Errorf("%s: expected in instances[] (%s), but the reader returned neither a row nor the shared id", c.File, c.InputState)
			}
		default:
			if !mentioned(failed, name) {
				t.Errorf("%s: expected in errors[], not as a row (%s); a consumer reading only instances[] would never see it", c.File, c.Trap)
			}
		}
	}
}

// duplicateID is the id the fixture repeats on purpose, to make the reader's lack of
// dedupe visible.
const duplicateID = "127.0.0.1_52391"

func mentioned(errs []string, name string) bool {
	for _, msg := range errs {
		if strings.Contains(msg, name) {
			return true
		}
	}
	return false
}

// TestConsumerDistinguishesMissingEmptyAndUnreadable is the empty-state test a
// workboard actually needs. A missing directory, an empty one and a directory whose
// every file is corrupt all yield zero rows, so a consumer that only counts rows
// cannot tell "dagrun is not installed" from "every dagrun record is corrupt", and
// renders one sentence for both.
func TestConsumerDistinguishesMissingEmptyAndUnreadable(t *testing.T) {
	t.Run("missing directory is not an error and is not created", func(t *testing.T) {
		absent := filepath.Join(t.TempDir(), "dagrun", "instances")
		instances, errs := ReadInstances(absent)
		if len(instances) != 0 || len(errs) != 0 {
			t.Fatalf("missing dir: got %d instances and %d errors, want 0 and 0", len(instances), len(errs))
		}
		if _, err := os.Stat(absent); !os.IsNotExist(err) {
			t.Fatalf("reading created %s; a read must not create the registry", absent)
		}
	})

	t.Run("empty directory is zero rows and zero errors", func(t *testing.T) {
		instances, errs := ReadInstances(t.TempDir())
		if len(instances) != 0 || len(errs) != 0 {
			t.Fatalf("empty dir: got %d instances and %d errors, want 0 and 0", len(instances), len(errs))
		}
	})

	t.Run("all-unreadable directory is zero rows and one error per file", func(t *testing.T) {
		dir := t.TempDir()
		for _, name := range []string{"foreign.json", "truncated.json"} {
			body, err := os.ReadFile(filepath.Join("testdata", "workboard", "mixed", name))
			if err != nil {
				t.Fatalf("read fixture %s: %v", name, err)
			}
			if err := os.WriteFile(filepath.Join(dir, name), body, 0o600); err != nil {
				t.Fatalf("seed %s: %v", name, err)
			}
		}
		instances, errs := ReadInstances(dir)
		if len(instances) != 0 {
			t.Fatalf("all-unreadable dir: got %d instances, want 0", len(instances))
		}
		if len(errs) != 2 {
			t.Fatalf("all-unreadable dir: got %d errors, want 2 (one per file)", len(errs))
		}
	})
}

// TestConsumerReadLeavesTheRegistryByteIdentical keeps the reader honest: a consumer
// polls, so a read that rewrote, reordered or dropped a file would turn a display bug
// into data loss.
func TestConsumerReadLeavesTheRegistryByteIdentical(t *testing.T) {
	for _, dir := range []string{"live", "mixed"} {
		path := filepath.Join("testdata", "workboard", dir)
		before := digestDir(t, path)
		if len(before) == 0 {
			t.Fatalf("%s: fixture is empty", path)
		}
		ReadInstances(path)
		after := digestDir(t, path)
		if len(before) != len(after) {
			t.Fatalf("%s: read changed the file count from %d to %d", path, len(before), len(after))
		}
		for name, sum := range before {
			if after[name] != sum {
				t.Fatalf("%s: read changed %s", path, name)
			}
		}
	}
}

func digestDir(t *testing.T, dir string) map[string]string {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read dir %s: %v", dir, err)
	}
	out := map[string]string{}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		body, err := os.ReadFile(filepath.Join(dir, e.Name()))
		if err != nil {
			t.Fatalf("read %s: %v", e.Name(), err)
		}
		sum := sha256.Sum256(body)
		out[e.Name()] = hex.EncodeToString(sum[:])
	}
	return out
}

// TestConsumerMustDedupeAndCheckIDAgainstOrigin states the two rules a consumer
// cannot take from the reader, because the reader enforces neither: it does not
// dedupe by id, and it accepts any non-empty id rather than checking that it names
// the origin. A consumer that trusts both renders two cards for one server and keys
// a map on a sentence.
func TestConsumerMustDedupeAndCheckIDAgainstOrigin(t *testing.T) {
	instances, _ := ReadInstances(filepath.Join("testdata", "workboard", "mixed"))

	byID := map[string]int{}
	for _, inst := range instances {
		byID[inst.ID]++
	}
	if got := byID[duplicateID]; got != 2 {
		t.Fatalf("the fixture's duplicated id appeared %d times, want 2; if the reader started deduping, the consumer's dedupe rule is now untested", got)
	}
	if _, ok := byID["not a valid id"]; !ok {
		t.Fatal("the mismatched-id record is no longer listed; if Validate started checking the id against the origin, the consumer rule is stale rather than wrong")
	}

	var mismatched int
	for _, inst := range instances {
		want, err := idForOrigin(inst.Origin)
		if err != nil {
			t.Fatalf("record %q has an origin that does not parse: %v", inst.ID, err)
		}
		if inst.ID != want {
			mismatched++
		}
	}
	if mismatched != 1 {
		t.Fatalf("expected exactly one row whose id does not name its origin, got %d", mismatched)
	}
}

// idForOrigin is the rule the writer applies in safeID: host with ':' turned into
// '-', then '_' and the port. It is derivable from the origin alone, which is what
// makes it a check a consumer can perform rather than a pattern to invent.
func idForOrigin(origin string) (string, error) {
	u, err := url.Parse(origin)
	if err != nil {
		return "", err
	}
	host := strings.NewReplacer(":", "-", "[", "", "]", "").Replace(u.Hostname())
	return host + "_" + u.Port(), nil
}

// TestConsumerFixtureManifestIsTheContract checks what a consumer fetches after the
// registry says hello: the manifest must still validate under this package's own
// rules, and a read-only surface must not advertise a write route.
func TestConsumerFixtureManifestIsTheContract(t *testing.T) {
	body, err := os.ReadFile(filepath.Join("testdata", "workboard", "manifest", "manifest.json"))
	if err != nil {
		t.Fatalf("read manifest fixture: %v", err)
	}
	var m Manifest
	if err := json.Unmarshal(body, &m); err != nil {
		t.Fatalf("decode manifest fixture: %v", err)
	}
	if err := m.Validate(); err != nil {
		t.Fatalf("the captured manifest no longer validates: %v", err)
	}
	if m.ID != ID {
		t.Fatalf("manifest id = %q, want %q; a consumer uses this to tell us from a squatter", m.ID, ID)
	}
	if m.Version == "" {
		t.Fatal("manifest version is empty; --verify accepts a record only when the id and a non-empty version both check out")
	}

	body, err = os.ReadFile(filepath.Join("testdata", "workboard", "manifest", "discovery.json"))
	if err != nil {
		t.Fatalf("read discovery fixture: %v", err)
	}
	var d Discovery
	if err := json.Unmarshal(body, &d); err != nil {
		t.Fatalf("decode discovery fixture: %v", err)
	}
	if len(d.Routes) == 0 {
		t.Fatal("discovery fixture has no routes")
	}
	for _, r := range d.Routes {
		if r.Method != "GET" {
			t.Errorf("route %s is %s; this surface is read-only", r.Path, r.Method)
		}
		if !r.ReadOnly {
			t.Errorf("route %s is not marked read_only", r.Path)
		}
		if r.Purpose == "" {
			t.Errorf("route %s has no purpose; a consumer renders it as the label", r.Path)
		}
	}
	if d.Mount.Path == "" || !d.Mount.ReadOnly {
		t.Errorf("mount %+v must name a read-only embed path", d.Mount)
	}
	if d.Authority.Writes {
		t.Error("authority claims writes; a consumer would think it may mutate the run")
	}
}
