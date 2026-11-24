package mcp

import (
	"context"
	"encoding/json"
)

// toolSpec is one registered MCP tool.
//
// It is the single source of truth for the catalogue. The stdio transport
// advertises toolList(), which renders these specs, and the HTTP transport
// registers the very same specs with the official Go SDK. Two catalogues would
// be free to drift, and a drifted catalogue is worse than either one: a client
// would be told a tool exists on one transport and not the other, and the
// difference would only show up in production.
//
// The handler lives here too, so a tool cannot be advertised without a way to
// run it. callTool looks a spec up by name and calls it; there is no second
// switch that could fall out of step with this list.
type toolSpec struct {
	// Name is what a client calls.
	Name string
	// Description is the summary MCP clients show the model.
	Description string
	// InputSchema is the JSON Schema for the tool's arguments. It is handed to
	// both transports unchanged, so both advertise the same schema.
	InputSchema map[string]any
	// call runs the tool.
	//
	// It returns the payload, whether the call is an error the caller should
	// see as a failed call, and a protocol-level error (an unknown tool, or
	// arguments that are not JSON) which the transports report as a
	// JSON-RPC error instead.
	call func(ctx context.Context, s *Server, in toolArgs, raw json.RawMessage) (any, bool, error)
}

// toolArgs is the union of the arguments the direct tools take.
//
// The tools that accept either a string or a list take their arguments raw
// instead, because one shared struct cannot express both shapes without
// failing a client that sent the other one.
type toolArgs struct {
	Dir        string `json:"dir"`
	Node       string `json:"node"`
	Role       string `json:"role"`
	Owner      string `json:"owner"`
	Reason     string `json:"reason"`
	File       string `json:"file"`
	Count      int    `json:"count"`
	TTLSeconds int    `json:"ttl_seconds"`
	Force      bool   `json:"force"`
	Reset      bool   `json:"reset"`
	// trace
	Limit int `json:"limit"`
	// submit
	URL    string `json:"url"`
	Token  string `json:"token"`
	Format string `json:"format"`
	// run
	MaxNodes int    `json:"max_nodes"`
	Template string `json:"template"`
	DryRun   bool   `json:"dry_run"`
}

// tool is the stdio wire shape of one tool definition.
//
// The field order and the JSON names are part of the wire contract: the stdio
// transport is byte-compatible with what shipped before the HTTP transport
// existed, and this struct is what produces those bytes.
type tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

// toolSpecs returns the catalogue, in the order it is advertised.
//
// The order is part of the stdio wire contract: tools/list returns this list
// as-is, so reordering it changes the bytes on the wire.
func toolSpecs() []toolSpec {
	dir := str("run directory holding run.yaml and state.json (default .dagrun)")
	node := str("node id, e.g. 1.2 or 4.1/auth-go")
	return []toolSpec{
		{
			Name:        "dagrun_next",
			Description: "List nodes that are ready to run: dependencies done, artifacts not yet valid. Returns the generated prompt so a caller can hand it to an agent.",
			InputSchema: obj(map[string]any{"dir": dir, "role": str("only nodes with this role"), "count": num("limit the number returned")}),
			call: func(ctx context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolNext(ctx, in.Dir, in.Role, in.Count)
			},
		},
		{
			Name:        "dagrun_claim",
			Description: "Atomically take a node for an owner. Fails when the node is done, leased, blocked on dependencies, or a concurrency cap is reached.",
			InputSchema: obj(map[string]any{"dir": dir, "node": node, "owner": str("owner identity"), "ttl_seconds": num("lease length in seconds (default 120)")}, "node"),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolClaim(in.Dir, in.Node, in.Owner, in.TTLSeconds)
			},
		},
		{
			Name:        "dagrun_done",
			Description: "Verify a node's declared artifacts and mark it done. Returns isError when the contract is not met and force is false.",
			InputSchema: obj(map[string]any{"dir": dir, "node": node, "force": boolean("mark done even when artifacts do not verify")}, "node"),
			call: func(ctx context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolDone(ctx, in.Dir, in.Node, in.Force)
			},
		},
		{
			Name:        "dagrun_fail",
			Description: "Mark a node failed with a reason.",
			InputSchema: obj(map[string]any{"dir": dir, "node": node, "reason": str("why")}, "node"),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolTerminal(in.Dir, in.Node, "dagrun_fail", in.Reason)
			},
		},
		{
			Name:        "dagrun_skip",
			Description: "Mark a node skipped with a reason.",
			InputSchema: obj(map[string]any{"dir": dir, "node": node, "reason": str("why")}, "node"),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolTerminal(in.Dir, in.Node, "dagrun_skip", in.Reason)
			},
		},
		{
			Name:        "dagrun_status",
			Description: "Run status: per-status counts, progress, and every node with attempts, owner, and last error.",
			InputSchema: obj(map[string]any{"dir": dir}),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolStatus(in.Dir)
			},
		},
		{
			Name:        "dagrun_validate",
			Description: "Re-check every node against the filesystem. Reports nodes recorded done that no longer verify, and nodes already satisfied that are not marked done.",
			InputSchema: obj(map[string]any{"dir": dir}),
			call: func(ctx context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolValidate(ctx, in.Dir)
			},
		},
		{
			Name:        "dagrun_plan",
			Description: "Validate a plan file, install it as the run, and return the PERT summary (waves, critical path).",
			InputSchema: obj(map[string]any{"dir": dir, "file": str("plan file to install"), "reset": boolean("discard existing progress")}),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolPlan(in.Dir, in.File, in.Reset)
			},
		},
		{
			Name:        "dagrun_explain",
			Description: "Diagnose one node: which predicate failed, why, and what to do next.",
			InputSchema: obj(map[string]any{"dir": dir, "node": node}, "node"),
			call: func(ctx context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolExplain(ctx, in.Dir, in.Node)
			},
		},
		{
			Name: "dagrun_trace",
			Description: "The merged execution trace: every event from every worker, in time order. " +
				"This is what happened, as opposed to what the state file says.",
			InputSchema: obj(map[string]any{"dir": dir, "limit": num("return only the last N events")}),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolTrace(in.Dir, in.Limit)
			},
		},
		{
			Name: "dagrun_submit",
			Description: "Post the run to a Tracera instance at /ingest/agileplus. " +
				"Fails loud: a non-2xx status is an error, and so is a 2xx whose report carries " +
				"a non-empty error list. Use dry_run to get the exact payload without sending it.",
			InputSchema: obj(map[string]any{
				"dir":     dir,
				"url":     str("Tracera base URL, e.g. http://localhost:3180"),
				"token":   str("NAME of the env var holding the bearer token; never the token itself"),
				"format":  str("tracera (default) or agileplus"),
				"dry_run": boolean("return the payload without sending it"),
			}),
			call: func(_ context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolSubmit(in.Dir, in.URL, in.Token, in.Format, in.DryRun)
			},
		},
		{
			Name: "dagrun_run",
			Description: "Execute ready nodes by spawning their harnesses, then return the summary. " +
				"BOUNDED: stops after max_nodes (default 1) so one call cannot hang a client. " +
				"An agent that wants to drive the whole run should loop next -> claim -> done " +
				"instead, so it owns each node rather than handing the run to the executor.",
			InputSchema: obj(map[string]any{
				"dir":       dir,
				"max_nodes": num("how many nodes to attempt before returning (default 1)"),
				"owner":     str("owner identity recorded on each claim"),
				"template":  str("shell command to run for nodes that name no harness"),
				"dry_run":   boolean("decide what would run without spawning anything"),
			}),
			call: func(ctx context.Context, s *Server, in toolArgs, _ json.RawMessage) (any, bool, error) {
				return s.toolRun(ctx, in.Dir, in.Owner, in.Template, in.MaxNodes, in.DryRun)
			},
		},
		// The seven tools below are the verbs an agent needs to DRIVE a run.
		// They live in tools_more.go; see that file for why viz, otel,
		// timeline, review and critique are deliberately absent.
		{
			Name: "dagrun_query",
			Description: "Select nodes with a structured query: filter with where, project with select, " +
				"order and limit. Read-only: it never opens the store, so it cannot create a run.",
			InputSchema: obj(map[string]any{
				"dir":      dir,
				"where":    stringListSchema("predicates such as status=failed, kind=DOC, attempt>=2, artifact=src/x.go"),
				"select":   stringListSchema("fields to return: " + "id, status, kind, role, owner, title, attempts, artifacts, progress"),
				"order_by": str("field to sort by, optionally with a direction: status,desc"),
				"limit":    num("return at most N rows (0 means no limit)"),
			}),
			call: moreTool("dagrun_query"),
		},
		{
			Name: "dagrun_recover",
			Description: "Report nodes stuck in a running state, with owner, lease and attempt count. " +
				"With force=false (the default) this only reports. With force=true it reclaims the " +
				"named nodes, or every stuck node when none are named, so they can be claimed again.",
			InputSchema: obj(map[string]any{
				"dir":   dir,
				"nodes": listSchema("node ids to reclaim; omit to reclaim every node reported stuck"),
				"force": boolean("actually reclaim instead of only reporting"),
			}),
			call: moreTool("dagrun_recover"),
		},
		{
			Name: "dagrun_replan",
			Description: "Diff a revised plan against the installed one and report what it would invalidate. " +
				"READ-ONLY by default: it shows the changes and any blocking nodes, and adopts nothing. " +
				"Pass apply=true to install the revision; force=true is a separate opt-in that discards " +
				"work which no longer verifies, so refusing to discard verified work stays the default.",
			InputSchema: obj(map[string]any{
				"dir":   dir,
				"file":  str("revised plan file to diff against the installed run.yaml"),
				"apply": boolean("install the revision (default false: diff only)"),
				"force": boolean("allow the revision to discard work that no longer verifies"),
			}, "file"),
			call: moreTool("dagrun_replan"),
		},
		{
			Name:        "dagrun_stats",
			Description: "Per-kind duration, adoption and retry statistics for the run, as both a structure and a rendered table.",
			InputSchema: obj(map[string]any{"dir": dir}),
			call:        moreTool("dagrun_stats"),
		},
		{
			Name:        "dagrun_lint",
			Description: "Run the semantic plan linter over the installed plan: well-formed but wrong problems. Advisory findings are warn: prefixed and do not fail the call.",
			InputSchema: obj(map[string]any{"dir": dir}),
			call:        moreTool("dagrun_lint"),
		},
		{
			Name:        "dagrun_doctor",
			Description: "Read-only health check of the run directory: missing plan, unwritable paths, harness availability, stale worktrees. Reports a missing plan as a finding rather than failing.",
			InputSchema: obj(map[string]any{"dir": dir}),
			call:        moreTool("dagrun_doctor"),
		},
		{
			Name: "dagrun_export",
			Description: "Emit the run for another system as json, agileplus, or tracera. " +
				"Returns the rendered document as text so its key order stays stable.",
			InputSchema: obj(map[string]any{
				"dir":    dir,
				"format": str("json (default) | agileplus | tracera"),
			}),
			call: moreTool("dagrun_export"),
		},
	}
}

// moreTool binds one of the seven tools that live in tools_more.go.
//
// They take the raw arguments rather than the shared struct because several of
// them accept a field that is either a string or a list, which one shared
// struct cannot express without failing a client that sent the other shape.
func moreTool(name string) func(context.Context, *Server, toolArgs, json.RawMessage) (any, bool, error) {
	return func(ctx context.Context, s *Server, _ toolArgs, raw json.RawMessage) (any, bool, error) {
		return s.toolMore(ctx, name, raw)
	}
}

// toolList renders the catalogue in the stdio wire shape.
func toolList() []tool {
	specs := toolSpecs()
	out := make([]tool, 0, len(specs))
	for _, spec := range specs {
		out = append(out, tool{
			Name:        spec.Name,
			Description: spec.Description,
			InputSchema: spec.InputSchema,
		})
	}
	return out
}

// lookupTool finds a spec by name.
func lookupTool(name string) (toolSpec, bool) {
	for _, spec := range toolSpecs() {
		if spec.Name == name {
			return spec, true
		}
	}
	return toolSpec{}, false
}

// ToolNames returns the advertised tool names, in catalogue order.
//
// It is the one place a caller asks "what does dagrun expose", so the answer
// cannot differ between transports.
func ToolNames() []string {
	specs := toolSpecs()
	names := make([]string, 0, len(specs))
	for _, spec := range specs {
		names = append(names, spec.Name)
	}
	return names
}
