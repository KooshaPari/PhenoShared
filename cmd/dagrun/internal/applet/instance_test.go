package applet

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func newTestInstance(t *testing.T) Instance {
	t.Helper()
	inst, err := NewInstance("1.2.3", "/tmp/run", "127.0.0.1:52341", nil)
	if err != nil {
		t.Fatalf("NewInstance: %v", err)
	}
	return inst
}

func TestNewInstanceDerivesEveryURLFromOrigin(t *testing.T) {
	inst := newTestInstance(t)
	if inst.Contract != Contract {
		t.Fatalf("contract = %q, want %q", inst.Contract, Contract)
	}
	if inst.Origin != "http://127.0.0.1:52341" {
		t.Fatalf("origin = %q", inst.Origin)
	}
	if inst.Manifest != inst.Origin+ContractPath {
		t.Fatalf("manifest = %q, want %q", inst.Manifest, inst.Origin+ContractPath)
	}
	if inst.Discovery != inst.Origin+"/api/applet" {
		t.Fatalf("discovery = %q", inst.Discovery)
	}
	if inst.Embed != inst.Origin+"/embed" {
		t.Fatalf("embed = %q", inst.Embed)
	}
	if !inst.ReadOnly {
		t.Fatal("read_only must be true: this surface has no write path")
	}
	if inst.AllowOrigins == nil {
		t.Fatal("allow_origins must be an empty slice, not nil, so it marshals as [] not null")
	}
	if err := inst.Validate(); err != nil {
		t.Fatalf("own record does not validate: %v", err)
	}
}

func TestNewInstanceRefusesNonLoopback(t *testing.T) {
	for _, addr := range []string{
		"0.0.0.0:8080",   // every interface
		"192.168.1.5:80", // a LAN address
		"example.com:80", // a name is not an address we can prove is loopback
		"127.0.0.1",      // no port
	} {
		if _, err := NewInstance("v", "/d", addr, nil); err == nil {
			t.Fatalf("NewInstance(%q) was accepted; an unauthenticated surface must never be advertised off-host", addr)
		}
	}
}

func TestNewInstanceIPv6IDIsWindowsSafe(t *testing.T) {
	inst, err := NewInstance("v", "/d", "[::1]:9000", nil)
	if err != nil {
		t.Fatalf("NewInstance: %v", err)
	}
	if strings.ContainsAny(inst.ID, `:/\`) {
		t.Fatalf("id %q contains a character that is not safe in a file name on every supported host", inst.ID)
	}
	if _, err := inst.FileName(); err != nil {
		t.Fatalf("FileName: %v", err)
	}
	if inst.Origin != "http://[::1]:9000" {
		t.Fatalf("origin = %q, want the bracketed form", inst.Origin)
	}
	if err := inst.Validate(); err != nil {
		t.Fatalf("ipv6 record does not validate: %v", err)
	}
}

func TestInstanceValidateRejectsEachBrokenField(t *testing.T) {
	cases := []struct {
		name   string
		mutate func(*Instance)
		want   string
	}{
		{"foreign contract", func(i *Instance) { i.Contract = "urn:other" }, "contract"},
		{"no id", func(i *Instance) { i.ID = "" }, "id is empty"},
		{"unparseable origin", func(i *Instance) { i.Origin = "://x" }, "not a URL"},
		{"file scheme", func(i *Instance) { i.Origin = "file:///etc/passwd" }, "http or https"},
		{"remote origin", func(i *Instance) { i.Origin = "http://10.0.0.2:80" }, "not loopback"},
		{"origin with path", func(i *Instance) { i.Origin = "http://127.0.0.1:80/x" }, "has a path"},
		{"manifest off origin", func(i *Instance) { i.Manifest = "http://evil.example/.well-known/applet.json" }, "manifest"},
		{"embed off origin", func(i *Instance) { i.Embed = "http://evil.example/embed" }, "embed"},
		{"empty started_at", func(i *Instance) { i.StartedAt = "" }, "started_at"},
		{"non-RFC3339 started_at", func(i *Instance) { i.StartedAt = "yesterday" }, "RFC 3339"},
		{"claims writes", func(i *Instance) { i.ReadOnly = false }, "read_only is false"},
		{"nil allow_origins", func(i *Instance) { i.AllowOrigins = nil }, "allow_origins is nil"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			inst := newTestInstance(t)
			tc.mutate(&inst)
			err := inst.Validate()
			if err == nil {
				t.Fatalf("%s was accepted", tc.name)
			}
			if !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("error %q does not mention %q", err, tc.want)
			}
		})
	}
}

func TestInstanceValidateAcceptsLocalhostName(t *testing.T) {
	// `localhost` is not an IP literal, so net.ParseIP cannot prove loopback.
	// It is still this machine, and refusing it would break an operator who
	// pinned a name in --addr.
	inst := newTestInstance(t)
	inst.Origin = "http://localhost:8080"
	inst.Manifest = inst.Origin + ContractPath
	inst.Discovery = inst.Origin + "/api/applet"
	inst.Embed = inst.Origin + "/embed"
	if err := inst.Validate(); err != nil {
		t.Fatalf("localhost origin was rejected: %v", err)
	}
}

func TestInstanceRoundTripThroughDisk(t *testing.T) {
	dir := t.TempDir()
	inst := newTestInstance(t)
	path, err := inst.Write(dir)
	if err != nil {
		t.Fatalf("Write: %v", err)
	}
	if filepath.Dir(path) != dir {
		t.Fatalf("wrote %q outside the registry directory", path)
	}
	got, errs := ReadInstances(dir)
	if len(errs) != 0 {
		t.Fatalf("ReadInstances reported %v", errs)
	}
	if len(got) != 1 {
		t.Fatalf("got %d instances, want 1", len(got))
	}
	if !reflect.DeepEqual(got[0], inst) {
		t.Fatalf("round trip changed the record:\n got %+v\nwant %+v", got[0], inst)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("published file is missing: %v", err)
	}
}

func TestInstanceWriteLeavesNoTempFiles(t *testing.T) {
	dir := t.TempDir()
	inst := newTestInstance(t)
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("Write: %v", err)
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("ReadDir: %v", err)
	}
	for _, e := range entries {
		if strings.HasSuffix(e.Name(), ".tmp") {
			t.Fatalf("temp file %q survived the write; a reader could have seen it", e.Name())
		}
	}
}

func TestInstanceWriteReplacesItsOwnEntry(t *testing.T) {
	dir := t.TempDir()
	inst := newTestInstance(t)
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("first Write: %v", err)
	}
	inst.Version = "9.9.9"
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("second Write: %v", err)
	}
	got, errs := ReadInstances(dir)
	if len(errs) != 0 || len(got) != 1 {
		t.Fatalf("got %d instances and %d errors, want 1 and 0", len(got), len(errs))
	}
	if got[0].Version != "9.9.9" {
		t.Fatalf("version = %q, want the replacement", got[0].Version)
	}
}

func TestInstanceWriteRefusesAnInvalidRecord(t *testing.T) {
	dir := t.TempDir()
	inst := newTestInstance(t)
	inst.ReadOnly = false
	if _, err := inst.Write(dir); err == nil {
		t.Fatal("Write accepted a record that claims a write path")
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 0 {
		t.Fatalf("%d files were written for a rejected record", len(entries))
	}
}

func TestRemoveInstanceIsIdempotent(t *testing.T) {
	dir := t.TempDir()
	inst := newTestInstance(t)
	name, err := inst.FileName()
	if err != nil {
		t.Fatalf("FileName: %v", err)
	}
	if err := RemoveInstance(dir, name); err != nil {
		t.Fatalf("removing an absent entry failed: %v", err)
	}
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("Write: %v", err)
	}
	if err := RemoveInstance(dir, name); err != nil {
		t.Fatalf("first remove: %v", err)
	}
	if err := RemoveInstance(dir, name); err != nil {
		t.Fatalf("second remove: %v", err)
	}
	if err := RemoveInstance(dir, ""); err != nil {
		t.Fatalf("empty name: %v", err)
	}
	got, errs := ReadInstances(dir)
	if len(got) != 0 || len(errs) != 0 {
		t.Fatalf("directory is not empty after remove: %d instances, %d errors", len(got), len(errs))
	}
}

func TestReadInstancesOnMissingDirectoryIsEmptyNotAnError(t *testing.T) {
	got, errs := ReadInstances(filepath.Join(t.TempDir(), "does-not-exist"))
	if len(got) != 0 || len(errs) != 0 {
		t.Fatalf("a host with no registry should see nothing and no error, got %d/%d", len(got), len(errs))
	}
}

func TestReadInstancesKeepsGoodEntriesBesideBadOnes(t *testing.T) {
	dir := t.TempDir()
	good := newTestInstance(t)
	if _, err := good.Write(dir); err != nil {
		t.Fatalf("Write: %v", err)
	}
	// Three ways a file can be wrong, none of which may hide the good entry.
	write := func(name, body string) {
		t.Helper()
		if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0o600); err != nil {
			t.Fatalf("seed %s: %v", name, err)
		}
	}
	write("truncated.json", `{"contract":`)
	write("unknown-field.json", `{"contract":"`+Contract+`","surprise":1}`)
	stale, _ := json.Marshal(newTestInstance(t))
	var asMap map[string]any
	_ = json.Unmarshal(stale, &asMap)
	asMap["read_only"] = false
	body, _ := json.Marshal(asMap)
	write("claims-writes.json", string(body))

	got, errs := ReadInstances(dir)
	if len(got) != 1 || !reflect.DeepEqual(got[0], good) {
		t.Fatalf("good entry was lost beside bad files: %+v", got)
	}
	if len(errs) != 3 {
		t.Fatalf("got %d errors, want 3 (one per bad file): %v", len(errs), errs)
	}
}

func TestReadInstancesIgnoresNonJSONAndHiddenFiles(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{"README.md", ".hidden.json", "notes.txt"} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte("not an instance"), 0o600); err != nil {
			t.Fatalf("seed %s: %v", name, err)
		}
	}
	got, errs := ReadInstances(dir)
	if len(got) != 0 || len(errs) != 0 {
		t.Fatalf("unrelated files produced %d instances and %d errors", len(got), len(errs))
	}
}

func TestReadInstancesSortsNewestFirst(t *testing.T) {
	dir := t.TempDir()
	older := newTestInstance(t)
	older.StartedAt = "2026-01-01T00:00:00Z"
	newer := newTestInstance(t)
	newer.ID = "older"
	newer.StartedAt = "2026-06-01T00:00:00Z"
	for _, inst := range []Instance{older, newer} {
		if _, err := inst.Write(dir); err != nil {
			t.Fatalf("Write: %v", err)
		}
	}
	got, errs := ReadInstances(dir)
	if len(errs) != 0 {
		t.Fatalf("ReadInstances: %v", errs)
	}
	if len(got) != 2 {
		t.Fatalf("got %d instances, want 2", len(got))
	}
	if got[0].StartedAt != newer.StartedAt {
		t.Fatalf("first entry is %q, want the newest (%q)", got[0].StartedAt, newer.StartedAt)
	}
}

func TestDefaultInstanceDirHonoursTheOverride(t *testing.T) {
	t.Setenv(InstanceDirEnv, "/tmp/whatever-instances")
	dir, err := DefaultInstanceDir()
	if err != nil {
		t.Fatalf("DefaultInstanceDir: %v", err)
	}
	if dir != "/tmp/whatever-instances" {
		t.Fatalf("dir = %q, want the override", dir)
	}
}

func TestDefaultInstanceDirFallsBackToHome(t *testing.T) {
	t.Setenv(InstanceDirEnv, "")
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("XDG_CONFIG_HOME", "")
	dir, err := DefaultInstanceDir()
	if err != nil {
		t.Fatalf("DefaultInstanceDir: %v", err)
	}
	if !strings.HasPrefix(dir, home) {
		t.Fatalf("dir = %q, want a path under %q", dir, home)
	}
}

func TestInstanceFileNameRefusesTraversal(t *testing.T) {
	for _, id := range []string{"../escape", `a\b`, "a/b", ""} {
		inst := newTestInstance(t)
		inst.ID = id
		if _, err := inst.FileName(); err == nil {
			t.Fatalf("id %q was accepted as a file name", id)
		}
	}
}
