package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/KooshaPari/dagrun/internal/export"
	"github.com/KooshaPari/dagrun/internal/house"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/query"
	"github.com/KooshaPari/dagrun/internal/recover"
	"github.com/KooshaPari/dagrun/internal/replan"
	"github.com/KooshaPari/dagrun/internal/stats"
	"github.com/KooshaPari/dagrun/internal/trace"
)

// Seven more tools close the gap between the MCP surface and the CLI verbs an
// agent needs to DRIVE a run rather than merely observe one: select nodes,
// reclaim them when a lease rots, adopt a revised plan, measure the run, lint
// the plan, diagnose the directory, and hand the result to another system.
//
// Deliberately NOT here: viz, otel, timeline, review and critique. Each of
// those produces a file or a rendering for a human. An MCP client reads data,
// so shipping a rendered artifact over the wire would cost bytes and lose
// structure the client can already query for itself.
//
// Every handler below is a thin adapter: the body is argument plumbing, one
// call into the owning package, and the shared payload shape. None of them
// re-implements diffing, statistics or recovery. If logic is ever needed here,
// it belongs in the package the table names.

// moreArgs is the union of arguments the seven tools accept. Each handler reads
// only the fields its tool documents; the server already ignores unknown JSON
// fields, so a client cannot fail a call by being generous.
type moreArgs struct {
	Dir     string          `json:"dir"`
	File    string          `json:"file"`
	Where   json.RawMessage `json:"where"`
	Select  json.RawMessage `json:"select"`
	OrderBy string          `json:"order_by"`
	Limit   int             `json:"limit"`
	Force   bool            `json:"force"`
	Apply   bool            `json:"apply"`
	Nodes   []string        `json:"nodes"`
	Format  string          `json:"format"`
}

// toolMore dispatches the tools in this file. tools.go forwards the raw
// arguments untouched so each tool can accept the shape it documents (for
// example `where` is either a string or a list) without widening the shared
// argument struct the original twelve tools decode into.
func (s *Server) toolMore(ctx context.Context, name string, raw json.RawMessage) (any, bool, error) {
	var a moreArgs
	if len(raw) > 0 {
		if err := json.Unmarshal(raw, &a); err != nil {
			return nil, true, fmt.Errorf("invalid arguments: %w", err)
		}
	}
	switch name {
	case "dagrun_query":
		return s.toolQuery(a)
	case "dagrun_recover":
		return s.toolRecover(a)
	case "dagrun_replan":
		return s.toolReplan(a)
	case "dagrun_stats":
		return s.toolStats(a)
	case "dagrun_lint":
		return s.toolLint(a)
	case "dagrun_doctor":
		return s.toolDoctor(a)
	case "dagrun_export":
		return s.toolExport(a)
	}
	return nil, true, fmt.Errorf("unknown tool %q", name)
}

// absRunDir resolves the run directory without touching it.
//
// openRun is the sibling helper for tools that need the store. It calls
// store.Open, which CREATES the run directory and its state file. A query, a
// lint, or a health check must be able to describe a directory that does not
// exist yet without creating it, so those three take this path instead. Same
// default, same absolutisation, no side effects.
func absRunDir(dir string) (string, error) {
	if strings.TrimSpace(dir) == "" {
		dir = ".dagrun"
	}
	return filepath.Abs(dir)
}

// stringList accepts the three shapes a client plausibly sends for a list of
// strings: a JSON array, a single string, or a comma-separated string. Being
// liberal here turns a client's formatting choice into an answer instead of an
// argument error.
func stringList(raw json.RawMessage) ([]string, error) {
	if len(raw) == 0 {
		return nil, nil
	}
	var many []string
	if err := json.Unmarshal(raw, &many); err == nil {
		return many, nil
	}
	var one string
	if err := json.Unmarshal(raw, &one); err != nil {
		return nil, fmt.Errorf("expected a string or a list of strings, got %s", string(raw))
	}
	out := []string{}
	for _, part := range strings.Split(one, ",") {
		if p := strings.TrimSpace(part); p != "" {
			out = append(out, p)
		}
	}
	return out, nil
}

// toolQuery answers a structured question about the nodes.
//
// The query language is query.Parse's, reused verbatim: building a second
// filter syntax here would mean two dialects with two sets of subtle rules,
// and the run's own `dagrun query` would stop matching what MCP returns.
func (s *Server) toolQuery(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	where, err := stringList(a.Where)
	if err != nil {
		return nil, true, err
	}
	selects, err := stringList(a.Select)
	if err != nil {
		return nil, true, err
	}
	qargs := make([]string, 0, len(where)+3)
	for _, w := range where {
		qargs = append(qargs, "--where="+w)
	}
	if len(selects) > 0 {
		qargs = append(qargs, "--select="+strings.Join(selects, ","))
	}
	if strings.TrimSpace(a.OrderBy) != "" {
		qargs = append(qargs, "--order-by="+a.OrderBy)
	}
	if a.Limit > 0 {
		qargs = append(qargs, fmt.Sprintf("--limit=%d", a.Limit))
	}
	q, err := query.Parse(qargs)
	if err != nil {
		return nil, true, err
	}
	rows, err := query.Run(abs, q)
	if err != nil {
		return nil, true, err
	}
	var rendered bytes.Buffer
	if err := query.Render(&rendered, rows, q, true); err != nil {
		return nil, true, err
	}
	return map[string]any{
		"dir":      abs,
		"count":    len(rows),
		"rows":     rows,
		"rendered": rendered.String(),
	}, false, nil
}

// toolRecover reports nodes stuck in a running state, and reclaims them when
// the caller opts in.
//
// Reclaiming is not the default: an expired lease is evidence that a worker
// stopped heartbeating, not proof that it died, so the safe answer is a report
// a human or a supervising agent can read first.
func (s *Server) toolRecover(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	run, stuck, err := recover.Report(abs)
	if err != nil {
		return nil, true, err
	}
	payload := map[string]any{
		"dir":     abs,
		"run":     run,
		"stuck":   stuck,
		"count":   len(stuck),
		"applied": false,
	}
	if !a.Force {
		return payload, len(stuck) > 0, nil
	}
	ids := a.Nodes
	if len(ids) == 0 {
		for _, st := range stuck {
			ids = append(ids, st.ID)
		}
	}
	if len(ids) == 0 {
		// Nothing is stuck: reclaiming is a no-op, and saying so is more
		// useful than reporting an empty success the caller cannot check.
		payload["reclaimed"] = []string{}
		return payload, false, nil
	}
	reclaimed, err := recover.Reclaim(abs, ids)
	if err != nil {
		return nil, true, err
	}
	payload["applied"] = true
	payload["reclaimed"] = reclaimed
	return payload, false, nil
}

// toolReplan diffs a revised plan against the installed one.
//
// READ-ONLY unless the caller passes apply: true. That default is the whole
// point of the tool: the dangerous direction is silently adopting a revision
// that invalidates work the run already verified, so the diff is always shown
// and adoption is always an explicit second request. force is a separate
// opt-in because it discards verified work.
func (s *Server) toolReplan(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	if strings.TrimSpace(a.File) == "" {
		return nil, true, fmt.Errorf("file is required: the revised plan to diff")
	}
	installed, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, true, fmt.Errorf("no plan installed at %s: install one first", filepath.Join(abs, "run.yaml"))
		}
		return nil, true, err
	}
	old, err := plan.Parse(installed)
	if err != nil {
		return nil, true, fmt.Errorf("installed plan: %w", err)
	}
	revisedRaw, err := os.ReadFile(a.File)
	if err != nil {
		return nil, true, err
	}
	revised, err := plan.Parse(revisedRaw)
	if err != nil {
		return nil, true, fmt.Errorf("%s: %w", a.File, err)
	}
	diff := plan.Diff(old, revised)
	payload := map[string]any{
		"dir":      abs,
		"file":     a.File,
		"safe":     diff.Safe,
		"changes":  diff.Changes,
		"blocking": diff.Blocking,
		"applied":  false,
	}
	if !a.Apply {
		payload["note"] = "read-only: pass apply=true to adopt the revision (force=true discards work that no longer verifies)"
		return payload, false, nil
	}
	res, err := replan.Apply(abs, revised, revisedRaw, a.Force)
	if err != nil {
		return nil, true, err
	}
	payload["applied"] = true
	payload["result"] = res
	return payload, false, nil
}

// toolStats reports per-kind duration, adoption and retry statistics.
//
// The package computes and renders; this adapter only carries both shapes
// back, because a client may want the numbers while a human reading the
// transcript wants the table.
func (s *Server) toolStats(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	rep, err := stats.Compute(abs)
	if err != nil {
		return nil, true, err
	}
	var rendered bytes.Buffer
	if err := stats.Render(&rendered, rep); err != nil {
		return nil, true, err
	}
	return map[string]any{
		"dir":      abs,
		"report":   rep,
		"rendered": rendered.String(),
	}, false, nil
}

// toolLint runs the semantic plan linter over the installed plan.
//
// Advisory findings are "warn:" prefixed and do not fail the call, exactly as
// `dagrun lint` treats them: a warning that turned into an error result here
// would train a client to ignore the result.
func (s *Server) toolLint(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	raw, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, true, fmt.Errorf("no plan installed at %s: call dagrun_plan first", filepath.Join(abs, "run.yaml"))
		}
		return nil, true, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, true, err
	}
	issues := p.SemanticIssues()
	errors, warnings := 0, 0
	for _, is := range issues {
		if strings.HasPrefix(is.Code, "warn:") {
			warnings++
		} else {
			errors++
		}
	}
	return map[string]any{
		"dir":      abs,
		"run":      p.Run,
		"ok":       errors == 0,
		"issues":   issues,
		"errors":   errors,
		"warnings": warnings,
	}, errors > 0, nil
}

// toolDoctor is a read-only health check of the run directory.
//
// It deliberately tolerates a directory with no plan: house.Doctor is designed
// to diagnose exactly that, and reporting "no plan installed" as a finding is
// more useful than failing the call with a transport error. The store and
// snapshot are passed only when the run can actually be opened, because
// opening a run creates it and doctor must not do that.
func (s *Server) toolDoctor(a moreArgs) (any, bool, error) {
	abs, err := absRunDir(a.Dir)
	if err != nil {
		return nil, true, err
	}
	var rep *house.Report
	if h, openErr := openRun(a.Dir); openErr == nil {
		rep = house.Doctor(abs, h.st, h.snap)
	} else {
		rep = house.Doctor(abs, nil, nil)
	}
	return map[string]any{
		"dir":     abs,
		"healthy": rep.Healthy(),
		"report":  rep,
	}, !rep.Healthy(), nil
}

// toolExport renders the run for another system.
//
// The payload is returned as text rather than re-encoded here: export.JSON
// already produces the canonical JSON, and marshalling it again through
// map[string]any would reorder keys and lose the stable output the export
// package guarantees.
func (s *Server) toolExport(a moreArgs) (any, bool, error) {
	h, err := openRun(a.Dir)
	if err != nil {
		return nil, true, err
	}
	events, err := trace.Merge(filepath.Join(h.st.Dir(), "trace"))
	if err != nil {
		return nil, true, err
	}
	in := export.Input{Plan: h.plan, State: h.snap, Events: events}

	format := strings.ToLower(strings.TrimSpace(a.Format))
	var data []byte
	switch format {
	case "":
		format = "json"
		data, err = export.JSON(in)
	case "json":
		data, err = export.JSON(in)
	case "agileplus", "agile-plus", "ap":
		data, err = export.AgilePlus(in)
	case "tracera", "trace":
		data, err = export.Tracera(in)
	default:
		// A refusal, not an argument error: the call was well-formed, the
		// format just is not one of ours. Reporting it as an error RESULT
		// keeps the allowed set in front of the caller instead of making
		// them guess from a transport error.
		return map[string]any{
			"ok":      false,
			"error":   fmt.Sprintf("unknown format %q; allowed formats are json, agileplus, tracera", a.Format),
			"allowed": []string{"json", "agileplus", "tracera"},
		}, true, nil
	}
	if err != nil {
		return nil, true, err
	}
	return map[string]any{
		"dir":     h.st.Dir(),
		"run":     h.plan.Run,
		"format":  format,
		"content": string(data),
	}, false, nil
}
