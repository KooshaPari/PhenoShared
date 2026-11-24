package applet

import (
	"fmt"
	"html/template"
	"strings"
)

// EmbedNode is one row of the embeddable view: a node and the little that a
// master console needs to place it, without the canvas, the card rail, or any
// way to act on it.
type EmbedNode struct {
	ID     string
	Title  string
	Kind   string
	Status string
	Owner  string
	// Session is reported as recorded. Validated says whether the harness's own
	// artifact store corroborated it, because an id nobody could check is a
	// claim, not an identity.
	Session   string
	Validated bool
	Attempts  int
	LastError string
	// Artifact counts come from the node's verify record: declared vs present.
	Artifacts int
	Missing   int
}

// Embed is everything the embedded page renders. It is a deliberately small
// projection: a console that wants more can read the API, and one that wants to
// act must use the CLI.
type Embed struct {
	Run     string
	Version string
	// Contract is published in the markup so a host can assert which applet
	// document it is looking at.
	Contract string
	// Dir is deliberately absent: the absolute path is operator state and an
	// embeddable surface has no reason to publish it.
	Nodes       []EmbedNode
	Counts      []Count
	Total       int
	ReadOnly    bool
	StatusPath  string
	FramePolicy string
}

// Count is one status cell: a status and how many nodes are in it.
type Count struct {
	Status string
	Count  int
}

// RenderEmbed renders the embeddable entrypoint.
//
// It has no form, no button and no input. That is the point: every interactive
// element on a surface like this is a candidate way to drive an agent from a
// second console, and this applet is an observer. The only script is a
// change-detector that reloads the page, which cannot write anything.
func RenderEmbed(e Embed) (string, error) {
	if e.Contract == "" {
		e.Contract = Contract
	}
	if e.StatusPath == "" {
		e.StatusPath = "/api/status"
	}
	e.ReadOnly = true
	var b strings.Builder
	if err := embedTmpl.Execute(&b, e); err != nil {
		return "", fmt.Errorf("render embed: %w", err)
	}
	return b.String(), nil
}

// embedTmpl is parsed once. html/template escapes every interpolated value, so a
// node title containing markup cannot become markup.
var embedTmpl = template.Must(template.New("embed").Funcs(template.FuncMap{
	// statusClass maps a status to a style hook. Unknown statuses stay neutral
	// rather than borrowing a decided one's colour.
	"statusClass": func(s string) string {
		switch s {
		case "done":
			return "ok"
		case "failed", "blocked":
			return "bad"
		case "running", "claimed":
			return "live"
		default:
			return "mute"
		}
	},
}).Parse(`<!DOCTYPE html>
<html lang="en" data-applet="{{.Contract}}" data-read-only="true">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{.Run}} · dagrun</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
         background: Canvas; color: CanvasText; }
  header { position: sticky; top: 0; display: flex; gap: 10px; align-items: baseline;
           padding: 8px 12px; border-bottom: 1px solid color-mix(in oklab, CanvasText 18%, Canvas);
           background: Canvas; flex-wrap: wrap; }
  header .run { font-weight: 600; }
  header .meta { opacity: .6; font-size: 11px; }
  header .ro { margin-left: auto; font-size: 11px; opacity: .7; }
  ul.counts { display: flex; gap: 6px; list-style: none; margin: 0; padding: 0; }
  ul.counts li { padding: 1px 6px; border-radius: 3px;
                 border: 1px solid color-mix(in oklab, CanvasText 20%, Canvas); }
  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; padding: 4px 12px; border-bottom: 1px solid
           color-mix(in oklab, CanvasText 10%, Canvas); vertical-align: top; }
  th { font-weight: 600; font-size: 11px; opacity: .7; position: sticky; top: 37px;
       background: Canvas; }
  td.id { width: 3em; } td.status { width: 7em; }
  .s { font-size: 11px; padding: 1px 6px; border-radius: 3px; white-space: nowrap;
       border: 1px solid currentColor; }
  .s.ok { } .s.bad { } .s.live { } .s.mute { opacity: .65; }
  .sub { display: block; font-size: 11px; opacity: .6; }
  .err { display: block; font-size: 11px; color: color-mix(in oklab, red 70%, CanvasText); }
  .unverified { text-decoration: underline dotted; }
  .empty { padding: 16px 12px; opacity: .6; }
</style>
</head>
<body>
<header>
  <span class="run">{{.Run}}</span>
  <span class="meta">dagrun {{.Version}}</span>
  <ul class="counts" aria-label="node status counts">
    {{- range .Counts }}
    <li><span class="s {{statusClass .Status}}">{{.Status}}</span> {{.Count }}</li>
    {{- end }}
  </ul>
  <span class="ro" title="this surface never writes">read-only · {{.Total}} nodes</span>
</header>
{{- if .Nodes }}
<table>
  <thead>
    <tr><th>#</th><th>status</th><th>title</th><th>agent</th></tr>
  </thead>
  <tbody>
  {{- range .Nodes }}
    <tr data-node="{{.ID}}" data-status="{{.Status}}">
      <td class="id">{{.ID}}</td>
      <td class="status"><span class="s {{statusClass .Status}}">{{.Status}}</span></td>
      <td>
        {{.Title}}
        {{- if .Kind }}<span class="sub">{{.Kind}}</span>{{ end }}
        {{- if .Missing }}<span class="sub">{{.Missing}} artifact(s) missing of {{.Artifacts}}</span>{{ end }}
        {{- if .LastError }}<span class="err">{{.LastError}}</span>{{ end }}
      </td>
      <td>
        {{- if .Owner }}{{ .Owner }}{{ else }}<span class="sub">unassigned</span>{{ end }}
        {{- if .Session }}
          {{- if .Validated }}
          <span class="sub">{{.Session}}</span>
          {{- else }}
          <span class="sub unverified" title="the harness artifact store did not corroborate this id">{{.Session}} (unvalidated)</span>
          {{- end }}
        {{- end }}
        {{- if gt .Attempts 1 }}<span class="sub">{{.Attempts}} attempts</span>{{ end }}
      </td>
    </tr>
  {{- end }}
  </tbody>
</table>
{{- else }}
<p class="empty">no nodes in this run</p>
{{- end }}
<script>
// Change detector only: a reload, never a write. The embed is deliberately
// stateless, so the cheapest correct refresh is to re-fetch the page.
(function () {
  var last = null;
  function tick() {
    fetch({{.StatusPath}}, {cache: 'no-store'})
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (last !== null && t !== last) { location.reload(); return; }
        last = t;
      })
      .catch(function () { /* a poll failure must not spam the parent console */ })
      .then(function () { setTimeout(tick, 3000); });
  }
  setTimeout(tick, 3000);
})();
</script>
</body>
</html>
`))
