package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/harness"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
	"github.com/KooshaPari/dagrun/internal/verify"
)

// The tool catalogue itself lives in registry.go, which is the single source
// both transports read. What is left here is how a tool runs.

func obj(props map[string]any, required ...string) map[string]any {
	schema := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func str(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func num(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func boolean(desc string) map[string]any {
	return map[string]any{"type": "boolean", "description": desc}
}

// stringListSchema and listSchema describe the two argument shapes that accept
// either a single value or several. They are schema helpers only, in the same
// spirit as str and boolean above.
func stringListSchema(desc string) map[string]any {
	return map[string]any{
		"type":        []any{"array", "string"},
		"items":       map[string]any{"type": "string"},
		"description": desc,
	}
}

func listSchema(desc string) map[string]any {
	return map[string]any{
		"type":        "array",
		"items":       map[string]any{"type": "string"},
		"description": desc,
	}
}

// runHandle is one opened run.
type runHandle struct {
	plan *plan.Plan
	st   *store.Store
	snap *store.State
}

func openRun(dir string) (*runHandle, error) {
	if strings.TrimSpace(dir) == "" {
		dir = ".dagrun"
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("no plan installed at %s: call dagrun_plan first", filepath.Join(abs, "run.yaml"))
		}
		return nil, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, err
	}
	cwd, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	p.Root = cwd
	st, err := store.Open(abs, p, raw, false)
	if err != nil {
		return nil, err
	}
	snap, err := st.Snapshot()
	if err != nil {
		return nil, err
	}
	return &runHandle{plan: p, st: st, snap: snap}, nil
}

func (h *runHandle) find(id string) *plan.Node {
	for _, n := range h.st.All(h.snap) {
		if n != nil && n.ID == id {
			return n
		}
	}
	return nil
}

func (h *runHandle) index() map[string]*plan.Node {
	m := map[string]*plan.Node{}
	for _, n := range h.st.All(h.snap) {
		if n != nil {
			m[n.ID] = n
		}
	}
	return m
}

// callTool dispatches one tools/call.
//
// The catalogue and the handlers live in one place (registry.go), so the tool a
// client is told about and the tool that runs cannot be two different lists.
//
// The arguments are parsed before the name is resolved, exactly as before: a
// client that sends an unknown tool with malformed arguments is told the
// arguments are malformed, not that the tool is unknown. Changing that would
// change the bytes on the wire.
func (s *Server) callTool(ctx context.Context, name string, raw json.RawMessage) (any, bool, error) {
	var in toolArgs
	if len(raw) > 0 {
		if err := json.Unmarshal(raw, &in); err != nil {
			return nil, true, fmt.Errorf("invalid arguments: %w", err)
		}
	}
	spec, ok := lookupTool(name)
	if !ok {
		return nil, true, fmt.Errorf("unknown tool %q", name)
	}
	return spec.call(ctx, s, in, raw)
}

func (s *Server) toolPlan(dir, file string, reset bool) (any, bool, error) {
	if strings.TrimSpace(file) == "" {
		return nil, true, fmt.Errorf("file is required")
	}
	raw, err := os.ReadFile(file)
	if err != nil {
		return nil, true, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, true, err
	}
	cwd, err := os.Getwd()
	if err != nil {
		return nil, true, err
	}
	p.Root = cwd
	if issues := p.Validate(); len(issues) > 0 {
		msgs := make([]string, 0, len(issues))
		for _, is := range issues {
			msgs = append(msgs, is.String())
		}
		return map[string]any{"ok": false, "issues": msgs}, true, nil
	}
	if strings.TrimSpace(dir) == "" {
		dir = ".dagrun"
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, true, err
	}
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return nil, true, err
	}
	if err := os.WriteFile(filepath.Join(abs, "run.yaml"), raw, 0o644); err != nil {
		return nil, true, err
	}
	if _, err := store.Open(abs, p, raw, reset); err != nil {
		return nil, true, err
	}
	sched := p.Pert()
	return map[string]any{
		"ok":       true,
		"run":      p.Run,
		"dir":      abs,
		"nodes":    len(p.Nodes),
		"waves":    sched.Waves,
		"critical": sched.Critical,
	}, false, nil
}

func (s *Server) toolNext(ctx context.Context, dir, role string, count int) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	idx := h.index()
	type ready struct {
		ID       string `json:"id"`
		Kind     string `json:"kind"`
		Title    string `json:"title"`
		Role     string `json:"role"`
		Harness  string `json:"harness"`
		Resolved string `json:"resolved,omitempty"`
		Provider string `json:"provider,omitempty"`
		Model    string `json:"model,omitempty"`
		Prompt   string `json:"prompt"`
	}
	out := []ready{}
	for _, n := range h.st.All(h.snap) {
		if n == nil || n.FanOut != "" {
			continue
		}
		ns := h.snap.Nodes[n.ID]
		if ns == nil || ns.Status != plan.StatusPending {
			continue
		}
		if !h.st.DepsDone(h.snap, n.ID) {
			continue
		}
		if role != "" && n.Role != role {
			continue
		}
		resolved := ""
		if a, rerr := harness.Resolve(n.Harness); rerr == nil && a != nil {
			resolved = a.Name
		}
		out = append(out, ready{
			ID: n.ID, Kind: n.Kind, Title: n.Title, Role: n.Role,
			Harness: n.Harness, Resolved: resolved, Provider: n.Provider, Model: n.Model,
			Prompt: plan.Prompt(h.plan, n, idx),
		})
		if count > 0 && len(out) >= count {
			break
		}
	}
	return map[string]any{"run": h.plan.Run, "ready": out, "count": len(out)}, false, nil
}

func (s *Server) toolClaim(dir, node, owner string, ttl int) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	if owner == "" {
		host, _ := os.Hostname()
		owner = fmt.Sprintf("mcp.%s.%d", host, os.Getpid())
	}
	d := time.Duration(ttl) * time.Second
	if d <= 0 {
		d = 2 * time.Minute
	}
	c, err := h.st.Claim(node, owner, d, time.Now())
	if err != nil {
		return nil, true, err
	}
	return map[string]any{"node": node, "owner": owner, "won": c.Won, "epoch": c.Epoch, "reason": c.Reason}, !c.Won, nil
}

func (s *Server) toolDone(ctx context.Context, dir, node string, force bool) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	n := h.find(node)
	if n == nil {
		return nil, true, fmt.Errorf("unknown node %q", node)
	}
	rep := verify.PlanNode(ctx, h.st.Root(), n, h.plan)
	if !rep.OK && !force {
		return map[string]any{"node": node, "ok": false, "report": rep, "hint": verify.Hint(n, rep)}, true, nil
	}
	reason := ""
	if !rep.OK {
		reason = "forced done over MCP"
	}
	if err := h.st.Force(node, plan.StatusDone, reason, &rep, time.Now()); err != nil {
		return nil, true, err
	}
	return map[string]any{"node": node, "ok": true, "forced": !rep.OK, "report": rep}, false, nil
}

func (s *Server) toolTerminal(dir, node, tool, reason string) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	if h.find(node) == nil {
		return nil, true, fmt.Errorf("unknown node %q", node)
	}
	status := plan.StatusFailed
	if tool == "dagrun_skip" {
		status = plan.StatusSkipped
	}
	if err := h.st.Force(node, status, reason, nil, time.Now()); err != nil {
		return nil, true, err
	}
	return map[string]any{"node": node, "status": status}, false, nil
}

func (s *Server) toolStatus(dir string) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	type row struct {
		ID        string `json:"id"`
		Kind      string `json:"kind"`
		Status    string `json:"status"`
		Attempts  int    `json:"attempts"`
		Owner     string `json:"owner,omitempty"`
		Branch    string `json:"branch,omitempty"`
		LastError string `json:"last_error,omitempty"`
		Dynamic   bool   `json:"dynamic,omitempty"`
	}
	var rows []row
	counts := map[string]int{}
	total, settled, dynamic := 0, 0, 0
	for _, n := range h.st.All(h.snap) {
		if n == nil {
			continue
		}
		ns := h.snap.Nodes[n.ID]
		if ns == nil {
			continue
		}
		counts[ns.Status]++
		if n.FanOut == "" {
			total++
			if ns.Status == plan.StatusDone {
				settled++
			}
		}
		isDynamic := strings.Contains(n.ID, "/")
		if isDynamic {
			dynamic++
		}
		rows = append(rows, row{
			ID: n.ID, Kind: n.Kind, Status: ns.Status, Attempts: ns.Attempts,
			Owner: ns.Owner, Branch: ns.Branch, LastError: ns.LastError,
			Dynamic: isDynamic,
		})
	}
	progress := 0.0
	if total > 0 {
		progress = float64(settled) / float64(total)
	}
	return map[string]any{
		"run": h.plan.Run, "counts": counts, "progress": progress,
		"nodes": rows, "dynamic": dynamic,
	}, false, nil
}

func (s *Server) toolValidate(ctx context.Context, dir string) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	broken, adoptable := 0, 0
	var findings []map[string]string
	for _, n := range h.st.All(h.snap) {
		if n == nil {
			continue
		}
		ns := h.snap.Nodes[n.ID]
		if ns == nil {
			continue
		}
		rep := verify.PlanNode(ctx, h.st.Root(), n, h.plan)
		if ns.Status == plan.StatusDone && !rep.OK {
			broken++
			findings = append(findings, map[string]string{"node": n.ID, "reason": rep.Reason})
		}
		if ns.Status != plan.StatusDone && rep.OK {
			adoptable++
		}
	}
	return map[string]any{"ok": broken == 0, "broken": broken, "adoptable": adoptable, "findings": findings}, broken > 0, nil
}

func (s *Server) toolExplain(ctx context.Context, dir, node string) (any, bool, error) {
	h, err := openRun(dir)
	if err != nil {
		return nil, true, err
	}
	n := h.find(node)
	if n == nil {
		return nil, true, fmt.Errorf("unknown node %q", node)
	}
	ns := h.snap.Nodes[node]
	rep := verify.PlanNode(ctx, h.st.Root(), n, h.plan)
	status := plan.StatusPending
	attempts := 0
	lastErr := ""
	if ns != nil {
		status, attempts, lastErr = ns.Status, ns.Attempts, ns.LastError
	}
	blockedBy := []string{}
	for _, d := range n.Deps {
		if ds := h.snap.Nodes[d]; ds != nil && ds.Status != plan.StatusDone && ds.Status != plan.StatusSkipped {
			blockedBy = append(blockedBy, d+"="+ds.Status)
		}
	}
	return map[string]any{
		"node": node, "kind": n.Kind, "title": n.Title, "status": status,
		"attempts": attempts, "last_error": lastErr, "blocked_by": blockedBy,
		"ok": rep.OK, "findings": rep.Artifacts, "check": rep.Check,
		"verdict": rep.Reason, "hint": verify.Hint(n, rep),
	}, !rep.OK, nil
}
