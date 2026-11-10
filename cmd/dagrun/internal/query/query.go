// Package query answers questions about a run without parsing prose.
//
// It is deliberately a QUERY, not a filter: you choose what to select, what to
// match, and how to order, and you get rows back. The reason is the failure mode
// it prevents. "Is anything still running?" and "which node owns file X?" are the
// questions an agent asks a hundred times a session, and answering them by
// re-reading `status` output is how an agent learns to guess.
//
// The package is read-only by construction: it reads run.yaml and state.json and
// never opens the store, because store.Open creates directories and a query must
// not change the thing it is describing.
package query

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"text/tabwriter"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// Row is one node, projected onto the fields a query can select.
type Row struct {
	ID        string `json:"id"`
	Status    string `json:"status"`
	Kind      string `json:"kind"`
	Role      string `json:"role"`
	Owner     string `json:"owner,omitempty"`
	Title     string `json:"title"`
	Attempts  int    `json:"attempts"`
	Artifacts int    `json:"artifacts"`
	Progress  string `json:"progress"`
}

// selectable is the closed set of fields. A query that asks for anything else is
// a typo, and silently returning nothing would make the typo look like an empty
// answer.
var selectable = map[string]bool{
	"id": true, "status": true, "kind": true, "role": true, "owner": true,
	"title": true, "attempts": true, "artifacts": true, "progress": true,
}

// whereKeys is the closed set of predicates.
var whereKeys = map[string]bool{
	"id": true, "status": true, "kind": true, "role": true, "owner": true,
	"attempt": true, "artifact": true,
}

// Predicate is one --where clause.
type Predicate struct {
	Key   string
	Op    string
	Value string
}

// Query is a parsed query.
type Query struct {
	Where   []Predicate
	Select  []string
	OrderBy string
	Desc    bool
	Limit   int
}

// DefaultSelect is what a bare `dagrun query` returns: enough to see the shape
// of the run without a wall of text.
var DefaultSelect = []string{"id", "status", "kind", "role", "title"}

// Parse reads the flag arguments. It exists so the CLI carries no query logic
// and any other surface (MCP, a test) can build the same query.
func Parse(args []string) (*Query, error) {
	q := &Query{Select: append([]string(nil), DefaultSelect...)}
	var selects []string

	for i := 0; i < len(args); i++ {
		a := args[i]
		name, value, inline := strings.Cut(a, "=")
		if !inline {
			// Every query flag takes a value, so the next argument is that value.
			if i+1 >= len(args) {
				return nil, fmt.Errorf("%s needs a value", a)
			}
			value = args[i+1]
			i++
		}
		switch name {
		case "--where":
			p, err := parsePredicate(value)
			if err != nil {
				return nil, err
			}
			q.Where = append(q.Where, p)
		case "--select":
			selects = append(selects, splitComma(value)...)
		case "--order-by":
			field, desc := value, false
			if f, d, ok := strings.Cut(value, ","); ok {
				field = f
				switch strings.ToLower(strings.TrimSpace(d)) {
				case "desc":
					desc = true
				case "asc", "":
				default:
					return nil, fmt.Errorf("--order-by %q: direction must be asc or desc", value)
				}
			}
			q.OrderBy = strings.TrimSpace(field)
			q.Desc = desc
		case "--limit":
			n, err := strconv.Atoi(value)
			if err != nil {
				return nil, fmt.Errorf("--limit %q is not a number", value)
			}
			q.Limit = n
		default:
			return nil, fmt.Errorf("unknown query flag %q; flags are --where, --select, --order-by, --limit", name)
		}
	}

	if len(selects) > 0 {
		q.Select = selects
	}
	if err := q.Validate(); err != nil {
		return nil, err
	}
	return q, nil
}

// parsePredicate reads `key=value`, `key>=value`, `key<=value`, `key>value`,
// `key<value`, and `key!=value`.
func parsePredicate(s string) (Predicate, error) {
	for _, op := range []string{"!=", ">=", "<=", ">", "<", "="} {
		if i := strings.Index(s, op); i > 0 {
			p := Predicate{Key: strings.TrimSpace(s[:i]), Op: op, Value: strings.TrimSpace(s[i+len(op):])}
			if p.Key == "" || p.Value == "" {
				return Predicate{}, fmt.Errorf("--where %q: both a key and a value are required", s)
			}
			return p, nil
		}
	}
	return Predicate{}, fmt.Errorf("--where %q: expected key=value, key>=value, key<=value, key>value, key<value or key!=value", s)
}

func splitComma(s string) []string {
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

// Validate checks the closed sets and the numeric ranges.
func (q *Query) Validate() error {
	if q.Limit < 0 {
		return fmt.Errorf("--limit must not be negative (0 means no limit)")
	}
	for _, f := range q.Select {
		if !selectable[f] {
			return fmt.Errorf("--select %q is not a field; allowed: %s", f, joinKeys(selectable))
		}
	}
	for _, p := range q.Where {
		if !whereKeys[p.Key] {
			return fmt.Errorf("--where key %q is not queryable; allowed: %s", p.Key, joinKeys(whereKeys))
		}
		if p.Key == "attempt" {
			switch p.Op {
			case "=", "!=", ">", ">=", "<", "<=":
			default:
				return fmt.Errorf("--where attempt only supports =, !=, >, >=, <, <=, got %q", p.Op)
			}
			if _, err := strconv.Atoi(p.Value); err != nil {
				return fmt.Errorf("--where attempt %q is not a number", p.Value)
			}
		}
	}
	if q.OrderBy != "" {
		if !selectable[q.OrderBy] {
			return fmt.Errorf("--order-by %q is not a field; allowed: %s", q.OrderBy, joinKeys(selectable))
		}
	}
	return nil
}

func joinKeys(m map[string]bool) string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return strings.Join(keys, ", ")
}

// Run reads a run directory and applies the query.
func Run(dir string, q *Query) ([]Row, error) {
	p, state, err := load(dir)
	if err != nil {
		return nil, err
	}

	rows := make([]Row, 0, len(p.Nodes))
	for _, n := range p.Nodes {
		if n == nil {
			continue
		}
		r := Row{
			ID:        n.ID,
			Kind:      n.Kind,
			Role:      n.Role,
			Title:     n.Title,
			Artifacts: len(n.Artifacts),
			Status:    plan.StatusPending,
		}
		if state != nil {
			if ns := state.Nodes[n.ID]; ns != nil {
				r.Status = ns.Status
				r.Owner = ns.Owner
				r.Attempts = ns.Attempts
				if ns.Verify != nil {
					ok := 0
					for _, a := range ns.Verify.Artifacts {
						if a.OK {
							ok++
						}
					}
					r.Progress = fmt.Sprintf("%d/%d", ok, len(n.Artifacts))
				}
			}
		}
		if r.Progress == "" {
			r.Progress = fmt.Sprintf("0/%d", len(n.Artifacts))
		}
		if !matches(r, n, q.Where) {
			continue
		}
		rows = append(rows, r)
	}

	orderRows(rows, q.OrderBy, q.Desc)
	if q.Limit > 0 && len(rows) > q.Limit {
		rows = rows[:q.Limit]
	}
	return rows, nil
}

// load reads the plan and, when present, the state. A run with no state yet is
// not an error: every node is simply pending, which is the truth.
func load(dir string) (*plan.Plan, *store.State, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		return nil, nil, fmt.Errorf("read plan in %s: %w", dir, err)
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, nil, fmt.Errorf("parse plan in %s: %w", dir, err)
	}
	sraw, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		if os.IsNotExist(err) {
			return p, nil, nil
		}
		return nil, nil, err
	}
	var st store.State
	if err := json.Unmarshal(sraw, &st); err != nil {
		return nil, nil, fmt.Errorf("parse state.json in %s: %w", dir, err)
	}
	return p, &st, nil
}

func matches(r Row, n *plan.Node, preds []Predicate) bool {
	for _, p := range preds {
		switch p.Key {
		case "id":
			if !globMatch(p.Value, r.ID) {
				return false
			}
		case "status":
			if !eqOrNot(p, r.Status) {
				return false
			}
		case "kind":
			if !eqOrNot(p, r.Kind) {
				return false
			}
		case "role":
			if !eqOrNot(p, r.Role) {
				return false
			}
		case "owner":
			if !eqOrNot(p, r.Owner) {
				return false
			}
		case "artifact":
			hit := false
			for _, a := range n.Artifacts {
				if strings.Contains(a.Path, p.Value) {
					hit = true
					break
				}
			}
			if p.Op == "!=" {
				if hit {
					return false
				}
			} else if !hit {
				return false
			}
		case "attempt":
			want, _ := strconv.Atoi(p.Value)
			if !compareInt(r.Attempts, p.Op, want) {
				return false
			}
		}
	}
	return true
}

// eqOrNot applies = and != case-insensitively. Any other operator on a string
// field is a mistake the caller should have caught in Validate; treating it as
// equality is the least surprising fallback, and it cannot hide a row.
func eqOrNot(p Predicate, got string) bool {
	same := strings.EqualFold(p.Value, got)
	if p.Op == "!=" {
		return !same
	}
	return same
}

func compareInt(got int, op string, want int) bool {
	switch op {
	case "=":
		return got == want
	case "!=":
		return got != want
	case ">":
		return got > want
	case ">=":
		return got >= want
	case "<":
		return got < want
	case "<=":
		return got <= want
	}
	return false
}

func orderRows(rows []Row, field string, desc bool) {
	if field == "" {
		field = "id"
	}
	less := func(a, b Row) bool {
		switch field {
		case "status":
			if a.Status != b.Status {
				return a.Status < b.Status
			}
		case "kind":
			if a.Kind != b.Kind {
				return a.Kind < b.Kind
			}
		case "role":
			if a.Role != b.Role {
				return a.Role < b.Role
			}
		case "owner":
			if a.Owner != b.Owner {
				return a.Owner < b.Owner
			}
		case "title":
			if a.Title != b.Title {
				return a.Title < b.Title
			}
		case "attempts":
			if a.Attempts != b.Attempts {
				return a.Attempts < b.Attempts
			}
		case "artifacts":
			if a.Artifacts != b.Artifacts {
				return a.Artifacts < b.Artifacts
			}
		case "progress":
			if a.Progress != b.Progress {
				return a.Progress < b.Progress
			}
		}
		// Always tiebreak on id: an order that is not total makes the output
		// differ between two identical runs.
		return plan.Less(a.ID, b.ID)
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if desc {
			return less(rows[j], rows[i])
		}
		return less(rows[i], rows[j])
	})
}

func globMatch(pattern, s string) bool {
	if pattern == "" {
		return true
	}
	pi, si := 0, 0
	star, mark := -1, 0
	for si < len(s) {
		switch {
		case pi < len(pattern) && (pattern[pi] == '?' || pattern[pi] == s[si]):
			pi++
			si++
		case pi < len(pattern) && pattern[pi] == '*':
			star, mark = pi, si
			pi++
		case star >= 0:
			pi = star + 1
			mark++
			si = mark
		default:
			return false
		}
	}
	for pi < len(pattern) && pattern[pi] == '*' {
		pi++
	}
	return pi == len(pattern)
}

// Render writes the rows. An empty result writes nothing to a table and `[]` to
// JSON, and returns no error: an empty answer is an answer, and exiting non-zero
// on it would train a caller to treat "nothing matched" as a failure.
func Render(w io.Writer, rows []Row, q *Query, asJSON bool) error {
	if asJSON {
		enc := json.NewEncoder(w)
		enc.SetIndent("", "  ")
		out := make([]map[string]any, 0, len(rows))
		for _, r := range rows {
			out = append(out, project(r, q.Select))
		}
		return enc.Encode(out)
	}
	if len(rows) == 0 {
		return nil
	}
	tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
	headers := make([]string, len(q.Select))
	for i, f := range q.Select {
		headers[i] = strings.ToUpper(f)
	}
	fmt.Fprintln(tw, strings.Join(headers, "\t"))
	for _, r := range rows {
		vals := make([]string, 0, len(q.Select))
		for _, f := range q.Select {
			vals = append(vals, fieldString(r, f))
		}
		fmt.Fprintln(tw, strings.Join(vals, "\t"))
	}
	return tw.Flush()
}

func project(r Row, fields []string) map[string]any {
	out := make(map[string]any, len(fields))
	for _, f := range fields {
		switch f {
		case "attempts":
			out[f] = r.Attempts
		case "artifacts":
			out[f] = r.Artifacts
		default:
			out[f] = fieldString(r, f)
		}
	}
	return out
}

func fieldString(r Row, f string) string {
	switch f {
	case "id":
		return r.ID
	case "status":
		return r.Status
	case "kind":
		return r.Kind
	case "role":
		return r.Role
	case "owner":
		return r.Owner
	case "title":
		return r.Title
	case "attempts":
		return strconv.Itoa(r.Attempts)
	case "artifacts":
		return strconv.Itoa(r.Artifacts)
	case "progress":
		return r.Progress
	}
	return ""
}
