package plan

// Reading phenotype-dag-core's DagSchema.
//
// Why this exists: the ecosystem had four DAG implementations and TWO of them
// defined a schema for the same thing. `crates/phenotype-dag-core` models a
// graph as nodes-plus-edges with prerequisites, acceptance criteria and audit
// hooks; dagrun models it as nodes-with-dependencies and an artifact contract.
// Until dagrun could read the other one, "one product" was a claim rather than a
// fact, and the collision was one directory move away from reappearing
// (ADR-ECO-024).
//
// The mapping is deliberately lossy and says so. DagSchema can express things
// dagrun's plan cannot (conditional edges, image/secret prerequisites), and
// dagrun can express things DagSchema cannot (artifact predicates, roles, CVP
// gates). What matters is that every field is either MAPPED or REPORTED, never
// silently dropped.

import (
	"fmt"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// DagSchema is phenotype-dag-core's portable DAG representation.
//
// The field names and the `type`-tagged enums mirror the Rust serde
// declarations exactly; see crates/phenotype-dag-core/src/{schema,serialize}.rs.
type DagSchema struct {
	Version string       `yaml:"version" json:"version"`
	Name    string       `yaml:"name,omitempty" json:"name,omitempty"`
	Nodes   []SchemaNode `yaml:"nodes,omitempty" json:"nodes,omitempty"`
	Edges   []SchemaEdge `yaml:"edges,omitempty" json:"edges,omitempty"`
}

// SchemaNode is one node in a DagSchema.
type SchemaNode struct {
	ID            string                `yaml:"id" json:"id"`
	Label         string                `yaml:"label,omitempty" json:"label,omitempty"`
	Description   string                `yaml:"description,omitempty" json:"description,omitempty"`
	Prerequisites []Prerequisite        `yaml:"prerequisites,omitempty" json:"prerequisites,omitempty"`
	Acceptance    []AcceptanceCriterion `yaml:"acceptance,omitempty" json:"acceptance,omitempty"`
	AuditHooks    []AuditHook           `yaml:"audit_hooks,omitempty" json:"audit_hooks,omitempty"`
	Metadata      map[string]string     `yaml:"metadata,omitempty" json:"metadata,omitempty"`
}

// SchemaEdge is one directed edge; `to` depends on `from`.
type SchemaEdge struct {
	From      string `yaml:"from" json:"from"`
	To        string `yaml:"to" json:"to"`
	Label     string `yaml:"label,omitempty" json:"label,omitempty"`
	Condition string `yaml:"condition,omitempty" json:"condition,omitempty"`
}

// Prerequisite is a pre-run condition: `type` plus its own fields.
//
// Variants as declared in phenotype-dag-core: image_ready, secret_available,
// resource_exists, api_healthy, file_exists, environment_variable,
// custom_script.
type Prerequisite struct {
	Type           string `yaml:"type" json:"type"`
	Image          string `yaml:"image,omitempty" json:"image,omitempty"`
	Name           string `yaml:"name,omitempty" json:"name,omitempty"`
	Provider       string `yaml:"provider,omitempty" json:"provider,omitempty"`
	ResourceType   string `yaml:"resource_type,omitempty" json:"resource_type,omitempty"`
	ID             string `yaml:"id,omitempty" json:"id,omitempty"`
	URL            string `yaml:"url,omitempty" json:"url,omitempty"`
	ExpectedStatus *int   `yaml:"expected_status,omitempty" json:"expected_status,omitempty"`
	Path           string `yaml:"path,omitempty" json:"path,omitempty"`
	Variable       string `yaml:"variable,omitempty" json:"variable,omitempty"`
	Command        string `yaml:"command,omitempty" json:"command,omitempty"`
	Description    string `yaml:"description,omitempty" json:"description,omitempty"`
}

// AcceptanceCriterion is a post-run condition: `type` plus its own fields.
//
// Variants as declared in phenotype-dag-core: exit_code, output_contains,
// http_ok, metric_threshold, log_check, custom_check.
type AcceptanceCriterion struct {
	Type           string   `yaml:"type" json:"type"`
	Code           *int     `yaml:"code,omitempty" json:"code,omitempty"`
	Pattern        string   `yaml:"pattern,omitempty" json:"pattern,omitempty"`
	Regex          bool     `yaml:"regex,omitempty" json:"regex,omitempty"`
	URL            string   `yaml:"url,omitempty" json:"url,omitempty"`
	ExpectedStatus *int     `yaml:"expected_status,omitempty" json:"expected_status,omitempty"`
	Metric         string   `yaml:"metric,omitempty" json:"metric,omitempty"`
	Min            *float64 `yaml:"min,omitempty" json:"min,omitempty"`
	Max            *float64 `yaml:"max,omitempty" json:"max,omitempty"`
	Negate         bool     `yaml:"negate,omitempty" json:"negate,omitempty"`
	Source         string   `yaml:"source,omitempty" json:"source,omitempty"`
	Command        string   `yaml:"command,omitempty" json:"command,omitempty"`
	Description    string   `yaml:"description,omitempty" json:"description,omitempty"`
}

// AuditHook is an audit/observability hook.
//
// It is an ENUM discriminated by `type`, not a {timing, script} pair: webhook,
// log_entry, metric_emit, notify all carry a `timing` (pre | post | on_success |
// on_failure) plus their own payload. Reading this correctly matters - a
// hand-written guess at this struct silently reads every hook as empty.
type AuditHook struct {
	Type    string            `yaml:"type" json:"type"`
	Timing  string            `yaml:"timing,omitempty" json:"timing,omitempty"`
	URL     string            `yaml:"url,omitempty" json:"url,omitempty"`
	Headers map[string]string `yaml:"headers,omitempty" json:"headers,omitempty"`
	Message string            `yaml:"message,omitempty" json:"message,omitempty"`
	Level   string            `yaml:"level,omitempty" json:"level,omitempty"`
	Name    string            `yaml:"name,omitempty" json:"name,omitempty"`
	Value   float64           `yaml:"value,omitempty" json:"value,omitempty"`
	Unit    string            `yaml:"unit,omitempty" json:"unit,omitempty"`
	Channel string            `yaml:"channel,omitempty" json:"channel,omitempty"`
}

// ParseDagSchema reads a DagSchema document.
func ParseDagSchema(raw []byte) (*DagSchema, error) {
	var d DagSchema
	if err := yaml.Unmarshal(raw, &d); err != nil {
		return nil, fmt.Errorf("parse DagSchema: %w", err)
	}
	if len(d.Nodes) == 0 {
		return nil, fmt.Errorf("DagSchema has no nodes")
	}
	return &d, nil
}

// SchemaUnmapped is one thing a DagSchema expressed that the plan cannot.
//
// It is returned rather than logged so a caller can refuse an import that loses
// something it cares about. A silent loss here would be exactly the kind of
// divergence this reader exists to prevent.
type SchemaUnmapped struct {
	Node   string
	Field  string
	Detail string
}

// ToPlan converts a DagSchema into a plan.
//
// Mapping rules, each of which is a lossy or lossless decision rather than an
// accident:
//
//   - `name` becomes the run name; an absent name falls back to "dagschema".
//   - node `id` is preserved verbatim. dagrun orders ids numerically per
//     dot-segment, so a DagSchema using "a"/"b" ids still works but sorts
//     lexically.
//   - `label` becomes the title. `description` is appended to the prompt: it is
//     the only field that tells a harness what the node is for.
//   - `acceptance` entries become CHECK commands, because a check is dagrun's
//     only post-run shell surface. `exit_code` and `output_contains` survive as
//     a one-line shell assertion; `http_ok` becomes a curl probe; anything
//     without a shell expression is reported.
//   - `prerequisites` become PRE hooks when they are a custom script, and are
//     reported otherwise: dagrun cannot provision a container image or fetch a
//     secret, and pretending to would fail the node for the wrong reason.
//   - `audit_hooks` map onto pre/post/on_fail by `timing`.
//   - an edge `to <- from` becomes a dependency of `to` on `from`. A CONDITIONAL
//     edge is reported, because dagrun has no conditional edges; dropping the
//     condition while keeping the dependency would silently make an edge
//     unconditional, which is worse than refusing.
//   - `metadata` is reported: a plan has no place for it, and inventing one
//     would add a field nobody reads.
func (d *DagSchema) ToPlan() (*Plan, []SchemaUnmapped, error) {
	p := &Plan{
		Version: 1,
		Run:     firstNonEmptyStr(d.Name, "dagschema"),
		Nodes:   make([]*Node, 0, len(d.Nodes)),
	}
	var unmapped []SchemaUnmapped

	known := make(map[string]bool, len(d.Nodes))
	for _, n := range d.Nodes {
		known[n.ID] = true
	}

	for _, sn := range d.Nodes {
		if strings.TrimSpace(sn.ID) == "" {
			return nil, unmapped, fmt.Errorf("DagSchema has a node with an empty id")
		}
		n := &Node{
			ID:    sn.ID,
			Kind:  "IMPL",
			Title: firstNonEmptyStr(sn.Label, sn.ID),
		}

		var prompt strings.Builder
		if sn.Description != "" {
			prompt.WriteString(sn.Description)
		}

		// Acceptance -> check. One check per node, so multiple criteria are
		// joined with && rather than silently keeping only the first.
		var checks []string
		for _, a := range sn.Acceptance {
			switch a.Type {
			case "exit_code":
				code := 0
				if a.Code != nil {
					code = *a.Code
				}
				if code == 0 {
					checks = append(checks, "true")
				} else {
					// dagrun cannot force a non-zero exit to mean success, so
					// this is a real gap rather than a mapping.
					unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "acceptance",
						Detail: fmt.Sprintf("exit_code %d is not expressible: a check must exit 0 to pass", code)})
				}
			case "output_contains":
				if a.Regex {
					checks = append(checks, fmt.Sprintf("printf '%%s' \"$DAGRUN_OUTPUT\" | grep -Eq %s", shellSingle(a.Pattern)))
				} else {
					checks = append(checks, fmt.Sprintf("printf '%%s' \"$DAGRUN_OUTPUT\" | grep -Fq %s", shellSingle(a.Pattern)))
				}
			case "custom_check":
				if a.Command == "" {
					unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "acceptance",
						Detail: "custom_check criterion has no command"})
					continue
				}
				checks = append(checks, a.Command)
			case "metric_threshold", "log_check":
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "acceptance",
					Detail: fmt.Sprintf("%s needs captured metrics or logs, which a plan check cannot read", a.Type)})
			case "http_ok":
				want := 200
				if a.ExpectedStatus != nil {
					want = *a.ExpectedStatus
				}
				checks = append(checks, fmt.Sprintf("test \"$(curl -s -o /dev/null -w '%%{http_code}' --max-time 10 %s)\" = %d",
					shellSingle(a.URL), want))
			default:
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "acceptance",
					Detail: fmt.Sprintf("criterion type %q has no shell equivalent in a plan", a.Type)})
			}
		}
		if len(checks) > 0 {
			n.Check = strings.Join(checks, " && ")
		}

		// Prerequisites -> pre hook, but only where a shell can express them.
		var pre []string
		for _, pr := range sn.Prerequisites {
			switch pr.Type {
			case "custom_script":
				if pr.Command != "" {
					pre = append(pre, pr.Command)
					continue
				}
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "prerequisites",
					Detail: "custom_script prerequisite has no command"})
			case "file_exists":
				pre = append(pre, fmt.Sprintf("test -e %s", shellSingle(pr.Path)))
			case "environment_variable":
				pre = append(pre, fmt.Sprintf("test -n \"${%s:-}\"", pr.Variable))
			case "api_healthy":
				pre = append(pre, fmt.Sprintf("curl -fsS --max-time 10 %s >/dev/null", shellSingle(pr.URL)))
			default:
				// image_ready / secret_available / resource_exists need
				// infrastructure dagrun cannot reach.
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "prerequisites",
					Detail: fmt.Sprintf("prerequisite type %q needs infrastructure dagrun cannot provision; the node is not gated on it", pr.Type)})
			}
		}

		// Audit hooks -> node hooks.
		//
		// Only `webhook` has a shell expression (a POST at a lifecycle point).
		// log_entry, metric_emit and notify target a telemetry sink dagrun does
		// not have, so they are reported rather than turned into a command that
		// would silently drop the payload.
		for _, h := range sn.AuditHooks {
			var cmd string
			switch h.Type {
			case "webhook":
				if h.URL == "" {
					unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "audit_hooks",
						Detail: "webhook hook has no url"})
					continue
				}
				payload := firstNonEmptyStr(h.Message, fmt.Sprintf("%s %s", "dagrun node", sn.ID))
				cmd = fmt.Sprintf("curl -fsS -X POST -H 'content-type: application/json' --data %s --max-time 10 %s >/dev/null",
					shellSingle(payload), shellSingle(h.URL))
			case "log_entry", "metric_emit", "notify":
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "audit_hooks",
					Detail: fmt.Sprintf("%s hook targets a telemetry sink dagrun does not have; the payload is not emitted", h.Type)})
				continue
			default:
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "audit_hooks",
					Detail: fmt.Sprintf("unknown hook type %q", h.Type)})
				continue
			}

			switch h.Timing {
			case "", "post":
				if n.Hooks == nil {
					n.Hooks = &Hooks{}
				}
				n.Hooks.Post = firstNonEmptyStr(n.Hooks.Post, cmd)
			case "pre":
				pre = append(pre, cmd)
			case "on_success":
				// dagrun's post hook runs only after a node verifies, which is
				// exactly on_success.
				if n.Hooks == nil {
					n.Hooks = &Hooks{}
				}
				n.Hooks.Post = firstNonEmptyStr(n.Hooks.Post, cmd)
			case "on_failure":
				if n.Hooks == nil {
					n.Hooks = &Hooks{}
				}
				n.Hooks.OnFail = firstNonEmptyStr(n.Hooks.OnFail, cmd)
			default:
				unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "audit_hooks",
					Detail: fmt.Sprintf("hook timing %q has no dagrun phase", h.Timing)})
			}
		}
		if len(pre) > 0 {
			if n.Hooks == nil {
				n.Hooks = &Hooks{}
			}
			n.Hooks.Pre = strings.Join(append([]string{n.Hooks.Pre}, pre...), " && ")
			n.Hooks.Pre = strings.TrimPrefix(n.Hooks.Pre, " && ")
		}

		if len(sn.Metadata) > 0 {
			keys := make([]string, 0, len(sn.Metadata))
			for k := range sn.Metadata {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			unmapped = append(unmapped, SchemaUnmapped{Node: sn.ID, Field: "metadata",
				Detail: fmt.Sprintf("metadata keys %s have no place in a plan", strings.Join(keys, ","))})
		}

		if prompt.Len() > 0 {
			n.Prompt = prompt.String()
		}
		p.Nodes = append(p.Nodes, n)
	}

	// Edges -> dependencies.
	byID := make(map[string]*Node, len(p.Nodes))
	for _, n := range p.Nodes {
		byID[n.ID] = n
	}
	for _, e := range d.Edges {
		to, ok := byID[e.To]
		if !ok {
			unmapped = append(unmapped, SchemaUnmapped{Node: e.To, Field: "edges",
				Detail: fmt.Sprintf("edge from %q targets node %q, which is not in the schema", e.From, e.To)})
			continue
		}
		if !known[e.From] {
			unmapped = append(unmapped, SchemaUnmapped{Node: e.To, Field: "edges",
				Detail: fmt.Sprintf("edge names a source node %q that is not in the schema", e.From)})
			continue
		}
		if e.Condition != "" {
			// Keeping the dependency but dropping the condition would make a
			// conditional edge unconditional, which is worse than refusing.
			unmapped = append(unmapped, SchemaUnmapped{Node: e.To, Field: "edges",
				Detail: fmt.Sprintf("edge %s -> %s is conditional (%q); dagrun has no conditional edges, so the condition is not applied",
					e.From, e.To, e.Condition)})
		}
		// Two edges between the same pair describe one dependency. Appending
		// twice would make the plan carry a duplicate, which every consumer then
		// has to defend against.
		dup := false
		for _, existing := range to.Deps {
			if existing == e.From {
				dup = true
				break
			}
		}
		if !dup {
			to.Deps = append(to.Deps, e.From)
		}
	}

	// A plan must not contain a cycle. DagSchema allows any edge set, so this is
	// checked here rather than left for `plan` to reject later with a less
	// useful message.
	if _, err := topoCheck(p); err != nil {
		return nil, unmapped, err
	}

	p.Normalize()
	return p, unmapped, nil
}

// topoCheck rejects a cycle so an imported schema fails where it was read.
func topoCheck(p *Plan) ([]string, error) {
	indeg := make(map[string]int, len(p.Nodes))
	adj := make(map[string][]string, len(p.Nodes))
	for _, n := range p.Nodes {
		indeg[n.ID] += 0
	}
	for _, n := range p.Nodes {
		for _, d := range n.Deps {
			adj[d] = append(adj[d], n.ID)
			indeg[n.ID]++
		}
	}
	queue := make([]string, 0, len(p.Nodes))
	for _, n := range p.Nodes {
		if indeg[n.ID] == 0 {
			queue = append(queue, n.ID)
		}
	}
	var order []string
	for len(queue) > 0 {
		sort.Strings(queue)
		cur := queue[0]
		queue = queue[1:]
		order = append(order, cur)
		for _, next := range adj[cur] {
			indeg[next]--
			if indeg[next] == 0 {
				queue = append(queue, next)
			}
		}
	}
	if len(order) != len(p.Nodes) {
		return nil, fmt.Errorf("DagSchema contains a cycle: %d of %d nodes are orderable", len(order), len(p.Nodes))
	}
	return order, nil
}

// shellSingle quotes a value for POSIX sh, so a pattern or URL containing a
// quote cannot break out of the generated check command.
func shellSingle(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func firstNonEmptyStr(vals ...string) string {
	for _, v := range vals {
		if strings.TrimSpace(v) != "" {
			return v
		}
	}
	return ""
}
