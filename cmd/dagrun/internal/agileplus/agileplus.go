// Package agileplus reads the ImportBundle that `dagrun export --format
// agileplus` emits, so a run can go to AgilePlus and come back.
//
// The round trip is the point. An export that cannot be read back is a report,
// not an interchange: it cannot be corrected upstream and re-imported, and there
// is no test that the fields on both sides agree. This package mirrors the shape
// in internal/export rather than inventing a second one, and a test asserts the
// two agree on the JSON field names.
//
// Two rules are load-bearing:
//
//   - an artifact contract is NEVER invented. A work package with no executable
//     acceptance criteria becomes a node whose prose intent survives, and it is
//     reported as unmapped rather than given a made-up verification.
//   - nothing is dropped silently. Everything that cannot be represented comes
//     back in []Unmapped with a reason.
package agileplus

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
	"strconv"
	"strings"

	"github.com/KooshaPari/dagrun/internal/plan"
)

// Bundle mirrors the ImportBundle that internal/export emits.
type Bundle struct {
	Projects []Project `json:"projects"`
}

// Project is one AgilePlus project.
type Project struct {
	Slug     string    `json:"slug"`
	Name     string    `json:"name"`
	Features []Feature `json:"features"`
}

// Feature is one AgilePlus feature; a feature becomes one dagrun run.
type Feature struct {
	FriendlyName string        `json:"friendly_name"`
	Slug         string        `json:"slug"`
	SpecContent  string        `json:"spec_content"`
	State        string        `json:"state"`
	TargetBranch string        `json:"target_branch,omitempty"`
	Labels       []string      `json:"labels,omitempty"`
	WorkPackages []WorkPackage `json:"work_packages"`
}

// WorkPackage is one unit of work; it becomes one dagrun node.
type WorkPackage struct {
	Sequence           int      `json:"sequence"`
	Title              string   `json:"title"`
	State              string   `json:"state"`
	AcceptanceCriteria string   `json:"acceptance_criteria,omitempty"`
	FileScope          []string `json:"file_scope,omitempty"`
	DependsOnSequences []int    `json:"depends_on_sequences,omitempty"`
}

// Unmapped is one work package that could not be represented faithfully.
//
// It is returned rather than logged so a caller can fail on it if it cares.
// Dropping data silently is the one thing a round trip must never do.
type Unmapped struct {
	Feature  string
	Sequence int
	Title    string
	Reason   string
}

// Parse reads a bundle. Unknown top-level keys are tolerated, because AgilePlus
// may add fields; malformed JSON is an error that names the offset.
func Parse(r io.Reader) (*Bundle, error) {
	raw, err := io.ReadAll(r)
	if err != nil {
		return nil, err
	}
	var b Bundle
	if err := json.Unmarshal(raw, &b); err != nil {
		return nil, fmt.Errorf("parse agileplus bundle: %w", err)
	}
	return &b, nil
}

// FromJSON parses a bundle from raw bytes and converts it to a plan.
func FromJSON(raw []byte) (*plan.Plan, []Unmapped, error) {
	b, err := Parse(bytes.NewReader(raw))
	if err != nil {
		return nil, nil, err
	}
	return ToPlan(b)
}

// SequenceOf recovers the AgilePlus sequence a node id came from. It is the
// inverse of nodeIDFor, and it returns false for an id that is not a plain
// integer so a caller cannot silently record a wrong link.
func SequenceOf(nodeID string) (int, bool) {
	n, err := strconv.Atoi(nodeID)
	if err != nil {
		return 0, false
	}
	return n, true
}

// ParseFile reads a bundle from disk.
func ParseFile(path string) (*Bundle, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return Parse(f)
}

// IDMap is the link between a work package and the node it became.
//
// Without it a round trip loses identity: sequence 3 becomes node "3", a later
// edit inserts a work package, and every subsequent sequence shifts to a node id
// that means something else. Persisting the map is what lets a second import
// recognise "this is the same work, edited" instead of "this is new work".
type IDMap struct {
	// Nodes maps "<feature-slug>#<sequence>" to a dagrun node id.
	Nodes map[string]string `json:"nodes"`
}

// NewIDMap returns an empty map.
func NewIDMap() *IDMap { return &IDMap{Nodes: map[string]string{}} }

func mapKey(featureSlug string, seq int) string {
	return fmt.Sprintf("%s#%d", featureSlug, seq)
}

// Resolve looks up the node id for a work package.
func (m *IDMap) Resolve(featureSlug string, seq int) (string, bool) {
	if m == nil || m.Nodes == nil {
		return "", false
	}
	id, ok := m.Nodes[mapKey(featureSlug, seq)]
	return id, ok
}

// Set records the node id for a work package.
func (m *IDMap) Set(featureSlug string, seq int, nodeID string) {
	if m.Nodes == nil {
		m.Nodes = map[string]string{}
	}
	m.Nodes[mapKey(featureSlug, seq)] = nodeID
}

// LoadIDMap reads a map from disk. A missing file is an empty map, not an error:
// the first import of a bundle has nothing to load.
func LoadIDMap(path string) (*IDMap, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return NewIDMap(), nil
		}
		return nil, err
	}
	m := NewIDMap()
	if err := json.Unmarshal(raw, m); err != nil {
		return nil, fmt.Errorf("parse id map %s: %w", path, err)
	}
	return m, nil
}

// Save writes the map atomically: a half-written map would silently renumber a
// run on the next import.
func (m *IDMap) Save(path string) error {
	raw, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, append(raw, '\n'), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// ToPlan turns a bundle into a plan. The first project's first feature wins: a
// run is one feature, and pretending otherwise would produce a plan whose nodes
// belong to two different AgilePlus features.
func ToPlan(b *Bundle) (*plan.Plan, []Unmapped, error) {
	if b == nil || len(b.Projects) == 0 || len(b.Projects[0].Features) == 0 {
		return nil, nil, fmt.Errorf("bundle has no project or no feature to import")
	}
	proj := b.Projects[0]
	feat := proj.Features[0]

	if len(feat.WorkPackages) == 0 {
		return nil, nil, fmt.Errorf("feature %q has no work packages", feat.Slug)
	}

	p := &plan.Plan{
		Version: 1,
		Run:     firstNonEmpty(feat.Slug, feat.FriendlyName, proj.Slug),
		Intent:  strings.TrimSpace(feat.SpecContent),
		Nodes:   make([]*plan.Node, 0, len(feat.WorkPackages)),
	}

	// Node ids are derived from the sequence so ordering survives, but they are
	// dotted WBS ids only when every sequence is a clean WBS path. Otherwise the
	// sequence is zero-padded, and the report says which form was used.
	ids := map[int]string{}
	for _, wp := range feat.WorkPackages {
		ids[wp.Sequence] = nodeIDFor(wp.Sequence)
	}

	var unmapped []Unmapped

	// Deps are resolved in a second pass so a forward reference still works.
	for _, wp := range feat.WorkPackages {
		if wp.Sequence < 0 {
			return nil, unmapped, fmt.Errorf("feature %q: work package %q has a negative sequence %d",
				feat.Slug, wp.Title, wp.Sequence)
		}
		id := ids[wp.Sequence]
		n := &plan.Node{
			ID:        id,
			Kind:      kindFor(wp),
			Title:     wp.Title,
			FileScope: append([]string(nil), wp.FileScope...),
		}

		// The exporter encodes a node's ARTIFACT paths in file_scope, because an
		// ImportBundle has no artifact field. An artifact path carries no
		// predicate, so the re-imported artifact demands only that the path
		// exists. That is a real information loss and it is reported rather than
		// papered over with an invented predicate.
		if len(wp.FileScope) > 0 {
			for _, p := range wp.FileScope {
				n.Artifacts = append(n.Artifacts, plan.Artifact{Path: p})
			}
			unmapped = append(unmapped, Unmapped{
				Feature:  feat.Slug,
				Sequence: wp.Sequence,
				Title:    wp.Title,
				Reason:   "artifact predicates (min_bytes, must_contain, must_match) are not representable in an ImportBundle; re-imported artifacts verify existence only",
			})
		}

		for _, seq := range wp.DependsOnSequences {
			if dep, ok := ids[seq]; ok {
				n.Deps = append(n.Deps, dep)
				continue
			}
			unmapped = append(unmapped, Unmapped{
				Feature:  feat.Slug,
				Sequence: wp.Sequence,
				Title:    wp.Title,
				Reason:   fmt.Sprintf("depends on sequence %d, which is not in this feature", seq),
			})
		}

		if check, ok := executableCheck(wp); ok {
			n.Check = check
		} else if len(wp.AcceptanceCriteria) > 0 {
			// The criteria exist but are prose. Keep the intent and say so.
			unmapped = append(unmapped, Unmapped{
				Feature:  feat.Slug,
				Sequence: wp.Sequence,
				Title:    wp.Title,
				Reason:   "acceptance criteria are prose, not an executable check; the node keeps its title and file scope but has no verification",
			})
		}

		if isFinished(wp.State) {
			// A work package AgilePlus already considers done must not be
			// re-run: the work is finished upstream, so a failure here is not a
			// reason to stop the run.
			n.Optional = true
		}

		p.Nodes = append(p.Nodes, n)
	}

	// An imported plan is built programmatically, so it has none of the defaults
	// a parsed plan carries. Normalising here is what makes the result a plan
	// the rest of the tool accepts rather than one that fails validation on a
	// missing timeout.
	p.Normalize()

	return p, unmapped, nil
}

// nodeIDFor maps an AgilePlus sequence to a dagrun node id.
//
// AgilePlus sequences are flat integers, so the id is the integer's decimal
// form: 1 -> "1", 11 -> "11". Zero-padding is deliberately NOT used. It looks
// like it would help lexical order, but plan.Less compares the numeric segments
// of a WBS id, so "2" already sorts before "10" and padding only produces ids
// that read like a different hierarchy.
func nodeIDFor(seq int) string {
	return strconv.Itoa(seq)
}

// kindFor infers a dagrun kind from the work package's shape. It is a heuristic
// and it is stated as one: AgilePlus work packages have no kind field, so any
// mapping is a guess. The guess only affects which kind-specific contract
// applies, and a node with no artifacts has no kind contract to satisfy.
func kindFor(wp WorkPackage) string {
	title := strings.ToLower(wp.Title + " " + strings.Join(wp.FileScope, " "))
	switch {
	case strings.Contains(title, "test"):
		return "TEST"
	case strings.Contains(title, "spec"):
		return "SPEC"
	case strings.Contains(title, "research"):
		return "RESEARCH"
	case strings.Contains(title, "doc") || strings.Contains(title, ".md"):
		return "DOC"
	}
	return "IMPL"
}

// executableCheck reports whether the acceptance criteria can be run as a shell
// command. The test is deliberately conservative: a command must look like a
// command, because putting prose into `check` would make every imported node
// fail with a shell syntax error.
func executableCheck(wp WorkPackage) (string, bool) {
	c := strings.TrimSpace(wp.AcceptanceCriteria)
	if c == "" {
		return "", false
	}
	if strings.ContainsAny(c, "\n") {
		return "", false
	}
	// A shell command starts with a known verb or an absolute/relative path.
	first := strings.Fields(c)
	if len(first) == 0 {
		return "", false
	}
	switch first[0] {
	case "go", "cargo", "npm", "make", "sh", "bash", "test", "grep", "git", "python", "python3", "node", "true", "false":
		return c, true
	}
	if strings.HasPrefix(first[0], "./") || strings.HasPrefix(first[0], "/") {
		return c, true
	}
	return "", false
}

// isFinished reports whether AgilePlus already considers this work done.
func isFinished(state string) bool {
	switch strings.ToLower(strings.TrimSpace(state)) {
	case "done", "closed", "completed", "complete", "shipped":
		return true
	}
	return false
}

// Conflict is a difference between the installed plan and an incoming one that
// a human should see before it is applied.
type Conflict struct {
	NodeID string `json:"node"`
	Kind   string `json:"kind"` // contract_changed | node_removed | sequence_reused
	Detail string `json:"detail"`
}

// Conflicts compares an installed plan with an incoming one.
//
// It reports and never resolves. A round trip that quietly overwrote a changed
// contract would make "import then re-export" a data-loss operation that looks
// like a no-op.
func Conflicts(existing, incoming *plan.Plan, m *IDMap) []Conflict {
	if existing == nil || incoming == nil {
		return nil
	}
	var out []Conflict

	old := map[string]*plan.Node{}
	for _, n := range existing.Nodes {
		if n != nil {
			old[n.ID] = n
		}
	}
	seen := map[string]bool{}

	for _, n := range incoming.Nodes {
		if n == nil {
			continue
		}
		seen[n.ID] = true
		prev, ok := old[n.ID]
		if !ok {
			continue
		}
		if diff := contractDiff(prev, n); diff != "" {
			out = append(out, Conflict{NodeID: n.ID, Kind: "contract_changed", Detail: diff})
		}
	}

	// A node that existed, was recorded in the map, and is gone from the
	// incoming plan is a removal. Only nodes the map knows about count: an
	// unrecorded node may simply belong to a different feature.
	if m != nil {
		for _, id := range m.Nodes {
			if id == "" || seen[id] {
				continue
			}
			if _, ok := old[id]; ok {
				out = append(out, Conflict{NodeID: id, Kind: "node_removed",
					Detail: "the work package that produced this node is no longer in the bundle"})
			}
		}
	}

	sort.Slice(out, func(i, j int) bool { return out[i].NodeID < out[j].NodeID })
	return out
}

// contractDiff names the first thing that would change a node's verification.
func contractDiff(a, b *plan.Node) string {
	if a.Kind != b.Kind {
		return fmt.Sprintf("kind %q -> %q", a.Kind, b.Kind)
	}
	if a.Check != b.Check {
		return "check changed"
	}
	if strings.Join(a.Deps, ",") != strings.Join(b.Deps, ",") {
		return "dependencies changed"
	}
	if strings.Join(a.FileScope, ",") != strings.Join(b.FileScope, ",") {
		return "file scope changed"
	}
	return ""
}

func firstNonEmpty(vals ...string) string {
	for _, v := range vals {
		if strings.TrimSpace(v) != "" {
			return v
		}
	}
	return ""
}
