// Package applet publishes one running dagrun as an applet: a manifest that
// conforms to the shared Phenotype applet contract, and a discovery document
// that adds the host-relative facts the contract deliberately leaves out.
//
// Two documents, because they answer to different owners.
//
//   - Manifest is the CONTRACT's document. Every field is defined by
//     urn:phenotype:atlas-plan:1:applet (docs/atlas/schemas/applet.schema.json),
//     which forbids additional properties, so nothing dagrun-specific may be
//     smuggled into it. A consumer that only knows the contract can validate it
//     and ignore everything else.
//   - Discovery is dagrun's own document. It embeds the manifest unmodified and
//     adds what the contract does not model: this instance's origin, the
//     embedding entrypoint, who owns the data and what the auth actually is.
//
// The manifest describes the PRODUCT (dagrun). The discovery describes one
// DEPLOYMENT of it (this run directory, on this loopback port). Conflating them
// is what makes an applet's metadata lie as soon as two instances exist.
//
// Nothing here is a control surface. Every capability below is a read, the only
// permission claimed is dagrun.read.observe, and the discovery states the write
// path plainly: none.
package applet

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

// Contract is the schema this manifest conforms to. A test pins it to the
// $id in the repository's own copy of the schema, so a contract bump that this
// package misses fails the build instead of shipping a stale document.
const Contract = "urn:phenotype:atlas-plan:1:applet"

// ContractPath is the discovery route the manifest is served from. It is under
// /.well-known/ because that is where a scanner looks first; /api/applet serves
// the wider Discovery document.
const ContractPath = "/.well-known/applet.json"

// ID is the applet's stable identity, not a run id. One product, many runs.
const ID = "dagrun"

// DefaultVersion is reported when the caller has no build version to hand.
const DefaultVersion = "0.0.0-dev"

// idPattern and the surface set below mirror the contract's own constraints.
// They are duplicated on purpose: a manifest is published to strangers, so it
// is validated on the way out rather than trusted because we wrote it.
var idPattern = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_.:-]*$`)

// surfaces are the contract's enum values this applet may claim.
var surfaces = map[string]bool{
	"library": true, "cli": true, "gui": true, "api": true,
	"mcp": true, "daemon": true, "audio": true, "video": true, "none": true,
}

// Port is one provided or required interface, named by contract id rather than
// by URL, because a port is a promise and a URL is a deployment detail.
type Port struct {
	Name       string `json:"name"`
	Direction  string `json:"direction"`
	ContractID string `json:"contract_id"`
}

// Manifest is the applet contract document. The field set and order are the
// contract's; none of it is optional, and no field may be added.
type Manifest struct {
	ID                   string   `json:"id"`
	Version              string   `json:"version"`
	SubjectID            string   `json:"subject_id"`
	ProvidedCapabilities []string `json:"provided_capabilities"`
	RequiredCapabilities []string `json:"required_capabilities"`
	OptionalCapabilities []string `json:"optional_capabilities"`
	Ports                []Port   `json:"ports"`
	OwnedStateIDs        []string `json:"owned_state_ids"`
	PermissionIDs        []string `json:"permission_ids"`
	ResourceProfileIDs   []string `json:"resource_profile_ids"`
	Surfaces             []string `json:"surfaces"`
	Children             []string `json:"children"`
	LifecycleContractID  string   `json:"lifecycle_contract_id"`
	FederationPolicy     string   `json:"federation_policy"`
	// Synthetic marks an illustrative record. This is a real running instance,
	// so it is false; a consumer must be able to rely on that.
	Synthetic bool `json:"synthetic"`
}

// Build returns the manifest for this build of dagrun.
//
// version is the binary's reported version. An empty one is reported as
// DefaultVersion rather than "" because the contract requires minLength 1, and
// publishing an invalid manifest is worse than publishing an unhelpful one.
func Build(version string) Manifest {
	if strings.TrimSpace(version) == "" {
		version = DefaultVersion
	}
	return Manifest{
		ID:        ID,
		Version:   strings.TrimSpace(version),
		SubjectID: "dagrun.run",
		ProvidedCapabilities: []string{
			"dagrun.plan.read",
			"dagrun.run.state.read",
			"dagrun.run.trace.read",
			"dagrun.run.agents.read",
			"dagrun.run.view.render",
		},
		// dagrun needs nothing from a peer to answer any of the above. Claiming
		// a requirement here would licence a host to gate a surface that in fact
		// works standalone.
		RequiredCapabilities: []string{},
		// The agent cards read harness session stores when they exist. That is a
		// genuine optional dependency: without it a card is unvalidated, not
		// missing, so the surface degrades instead of failing.
		OptionalCapabilities: []string{"dagrun.harness.session.read"},
		Ports: []Port{
			{Name: "read-api", Direction: "provides", ContractID: "dagrun.read-api.v1"},
			{Name: "embed-view", Direction: "provides", ContractID: "dagrun.embed-view.v1"},
			{Name: "applet-manifest", Direction: "provides", ContractID: "dagrun.applet-manifest.v1"},
			{Name: "run-directory", Direction: "requires", ContractID: "dagrun.run-directory.v1"},
		},
		OwnedStateIDs: []string{
			"dagrun.run.plan",
			"dagrun.run.state",
			"dagrun.run.trace",
			"dagrun.run.claims",
		},
		// The whole surface grants exactly one thing.
		PermissionIDs:      []string{"dagrun.read.observe"},
		ResourceProfileIDs: []string{"dagrun.loopback.readonly"},
		Surfaces:           []string{"api", "cli", "gui", "mcp"},
		// A run executes nodes; it does not compose other applets. An empty list
		// is the honest answer, not a placeholder.
		Children:            []string{},
		LifecycleContractID: "dagrun.serve.lifecycle.v1",
		FederationPolicy: "Read-only projection of one run directory. Data authority stays with the run " +
			"directory, which is owned by dagrun alone: a host may cache or re-present this document but " +
			"must not become a second writer. No route writes, claims a node or takes a lease. The server " +
			"binds loopback only and has no authentication of its own, so a host that presents it to a " +
			"remote surface is that host's responsibility and needs its own credentialed proxy. Embedding " +
			"is same-origin by default; a named consumer origin may be allow-listed explicitly, in which " +
			"case that origin can read this run's titles, statuses and session ids.",
		Synthetic: false,
	}
}

// Host is where this instance is reachable. It is deployment, not contract: a
// manifest served from a different port is the same applet.
type Host struct {
	Origin string `json:"origin,omitempty"`
	Addr   string `json:"addr,omitempty"`
	// Loopback is always true today. It is reported rather than assumed so a
	// consumer can see the binding's reach without fetching the code.
	Loopback bool `json:"loopback"`
}

// Mount is the embeddable entrypoint: the one URL a master console needs.
type Mount struct {
	Path string `json:"path"`
	Kind string `json:"kind"`
	// ReadOnly is always true. If this ever needs a false, the console has
	// stopped being an observer and the contract is the wrong one.
	ReadOnly bool `json:"read_only"`
	// FramePolicy is the effective CSP frame-ancestors value, so a host can
	// decide whether to iframe it without parsing a header.
	FramePolicy string `json:"frame_policy"`
	Notes       string `json:"notes,omitempty"`
}

// Auth states the security posture plainly. A document that omits it invites a
// host to guess, and the safe guess is not the true one here.
type Auth struct {
	Mode      string `json:"mode"`
	Scope     string `json:"scope"`
	Rationale string `json:"rationale"`
}

// Authority answers "who may write this data", which is the first question a
// federating host has and the one a manifest cannot express.
type Authority struct {
	Owner     string `json:"owner"`
	Writes    bool   `json:"writes"`
	Statement string `json:"statement"`
}

// Route is one endpoint this instance serves, with its method and purpose.
type Route struct {
	Path     string `json:"path"`
	Method   string `json:"method"`
	Purpose  string `json:"purpose"`
	ReadOnly bool   `json:"read_only"`
}

// Discovery is dagrun's own document: the manifest verbatim, plus the
// deployment facts the contract has no field for.
type Discovery struct {
	Contract  string    `json:"contract"`
	Applet    Manifest  `json:"applet"`
	Host      Host      `json:"host"`
	Mount     Mount     `json:"mount"`
	Auth      Auth      `json:"auth"`
	Authority Authority `json:"authority"`
	Routes    []Route   `json:"routes"`
}

// DiscoveryOptions is what the caller knows that Build cannot.
type DiscoveryOptions struct {
	Version string
	// Origin is the scheme://host:port a client used, when known. Empty for a
	// direct handler call, which is honest rather than invented.
	Origin string
	// Addr is the bound listen address.
	Addr string
	// FrameAncestors is the effective CSP value for the embed surface.
	FrameAncestors string
}

// NewDiscovery assembles the discovery document.
func NewDiscovery(opt DiscoveryOptions) Discovery {
	fa := opt.FrameAncestors
	if fa == "" {
		fa = SameOriginFrames
	}
	return Discovery{
		Contract: Contract,
		Applet:   Build(opt.Version),
		Host:     Host{Origin: opt.Origin, Addr: opt.Addr, Loopback: true},
		Mount: Mount{
			Path:        "/embed",
			Kind:        "http-html",
			ReadOnly:    true,
			FramePolicy: fa,
			Notes: "Renders this run's nodes and their statuses. No form, no button, no " +
				"prompt field: every control would be a way to drive an agent from a " +
				"second surface, which this applet does not offer.",
		},
		Auth: Auth{
			Mode:  "none-by-design",
			Scope: "loopback",
			Rationale: "The server binds 127.0.0.1/::1 only and refuses any other address, so the " +
				"reachability boundary is the security boundary. There is no token to fake and no " +
				"write to authorize. A deployment that needs a remote console terminates TLS and " +
				"authenticates in its own proxy; dagrun stays unauthenticated and loopback.",
		},
		Authority: Authority{
			Owner:  "dagrun",
			Writes: false,
			Statement: "dagrun owns run.yaml, state.json and trace/. This surface reads them directly " +
				"and never opens the store, so a monitor cannot sit on the write path. Writing is the " +
				"`dagrun run`/`claim`/`done` CLI's job, in the run directory, by the process holding it.",
		},
		Routes: []Route{
			{Path: ContractPath, Method: "GET", Purpose: "applet manifest, contract-valid only", ReadOnly: true},
			{Path: "/api/applet", Method: "GET", Purpose: "this document", ReadOnly: true},
			{Path: "/embed", Method: "GET", Purpose: "embeddable read-only view", ReadOnly: true},
			{Path: "/", Method: "GET", Purpose: "full interactive viewer", ReadOnly: true},
			{Path: "/api/health", Method: "GET", Purpose: "liveness and run id", ReadOnly: true},
			{Path: "/api/plan", Method: "GET", Purpose: "the installed plan", ReadOnly: true},
			{Path: "/api/status", Method: "GET", Purpose: "node status document", ReadOnly: true},
			{Path: "/api/agents", Method: "GET", Purpose: "agent cards, with session validation", ReadOnly: true},
			{Path: "/api/query", Method: "GET", Purpose: "query projection of the run", ReadOnly: true},
			{Path: "/api/nodes/{id}", Method: "GET", Purpose: "one node", ReadOnly: true},
		},
	}
}

// SameOriginFrames is the default CSP frame-ancestors value: only a document
// this origin served may frame it.
const SameOriginFrames = "'self'"

// FrameAncestors turns an allow-list of consumer origins into an effective CSP
// frame-ancestors value, always including this origin.
//
// It refuses anything that is not a bare http(s) origin. A wildcard, a path, a
// query, or a userinfo section would either widen the policy to every site or
// silently fail to match, and a silently non-matching allow-list is worse than
// a rejected one: the operator believes the embed works and it does not.
func FrameAncestors(origins []string) (string, error) {
	if len(origins) == 0 {
		return SameOriginFrames, nil
	}
	parts := []string{SameOriginFrames}
	seen := map[string]bool{SameOriginFrames: true}
	for _, raw := range origins {
		o, err := normalizeOrigin(raw)
		if err != nil {
			return "", err
		}
		if seen[o] {
			continue
		}
		seen[o] = true
		parts = append(parts, o)
	}
	return strings.Join(parts, " "), nil
}

// normalizeOrigin validates and canonicalises one consumer origin.
func normalizeOrigin(raw string) (string, error) {
	s := strings.TrimSpace(raw)
	if s == "" {
		return "", fmt.Errorf("empty origin in --embed-allow-origin")
	}
	if strings.Contains(s, "*") {
		return "", fmt.Errorf("origin %q contains a wildcard: name each consumer origin explicitly, because this surface has no authentication", raw)
	}
	u, err := url.Parse(s)
	if err != nil {
		return "", fmt.Errorf("origin %q is not a URL: %w", raw, err)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", fmt.Errorf("origin %q must be http or https", raw)
	}
	if u.Host == "" {
		return "", fmt.Errorf("origin %q has no host", raw)
	}
	if u.User != nil {
		return "", fmt.Errorf("origin %q carries credentials; frame-ancestors matches origins, not users", raw)
	}
	if u.Path != "" && u.Path != "/" {
		return "", fmt.Errorf("origin %q has a path; frame-ancestors matches origins only", raw)
	}
	if u.RawQuery != "" || u.Fragment != "" {
		return "", fmt.Errorf("origin %q has a query or fragment; frame-ancestors matches origins only", raw)
	}
	return u.Scheme + "://" + u.Host, nil
}
