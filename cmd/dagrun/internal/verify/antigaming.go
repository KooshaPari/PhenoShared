package verify

// Anti-gaming checks. The artifact loop proves a file exists and satisfies its
// declared predicates; these checks ask the harder question the predicates
// cannot: is there anything in it?
//
// They are separate from kinds.go because they are kind-agnostic. Slop is not a
// property of a SPEC or a DOC, it is a property of a document, and a node of any
// kind can be padded.

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
)

// placeholderMarkers are the strings that mean "this was never written".
//
// They are matched as whole words so "TODO_LIST_CONSTANT" in real code and
// "todos" in prose are not accusations. Case-insensitive, because the slop
// arrives in both cases.
var placeholderMarkers = []struct {
	Marker string
	re     *regexp.Regexp
}{
	{"TODO", regexp.MustCompile(`(?i)\bTODO\b`)},
	{"TBD", regexp.MustCompile(`(?i)\bTBD\b`)},
	{"FIXME", regexp.MustCompile(`(?i)\bFIXME\b`)},
	{"XXX", regexp.MustCompile(`\bXXX\b`)},
	{"lorem ipsum", regexp.MustCompile(`(?i)\blorem\s+ipsum\b`)},
	{"placeholder", regexp.MustCompile(`(?i)\bplaceholder\b`)},
	{"coming soon", regexp.MustCompile(`(?i)\bcoming\s+soon\b`)},
	{"not implemented", regexp.MustCompile(`(?i)\bnot\s+implemented\b`)},
}

// PlaceholderFindings reports placeholder markers left in an artifact.
//
// A code fence or an inline code span is skipped on purpose. A document ABOUT
// placeholders is not a placeholder, and the alternative — rejecting the very
// documentation that explains the rule — punishes the honest case.
//
// There is no allowlist. An artifact that declares allow_empty is still checked:
// empty is honest, a stub is not, and the two must not be confused just because
// both are cheap.
func PlaceholderFindings(name string, content []byte) []KindResult {
	lines := strings.Split(string(content), "\n")

	inFence := false
	firstSeen := map[string]int{}
	order := make([]string, 0, len(placeholderMarkers))
	for i, raw := range lines {
		trimmed := strings.TrimSpace(raw)
		if strings.HasPrefix(trimmed, "```") || strings.HasPrefix(trimmed, "~~~") {
			inFence = !inFence
			continue
		}
		if inFence {
			continue
		}
		// Strip inline code spans: a marker inside backticks is being quoted.
		line := stripInlineCode(raw)
		for _, m := range placeholderMarkers {
			if !m.re.MatchString(line) {
				continue
			}
			if _, ok := firstSeen[m.Marker]; !ok {
				firstSeen[m.Marker] = i + 1
				order = append(order, m.Marker)
			}
		}
	}

	out := make([]KindResult, 0, len(order))
	for _, marker := range order {
		out = append(out, KindResult{
			OK:     false,
			Code:   "placeholder_marker",
			Detail: fmt.Sprintf("%s contains %q at line %d", name, marker, firstSeen[marker]),
			Hint:   fmt.Sprintf("write the content that %q was standing in for, or drop the marker and the section", marker),
		})
	}
	return out
}

// stripInlineCode removes backticked spans so a quoted marker is not a finding.
// An unbalanced backtick is left alone: guessing where the span ended would
// silently hide real markers.
func stripInlineCode(line string) string {
	if strings.Count(line, "`") < 2 {
		return line
	}
	var b strings.Builder
	in := false
	for _, r := range line {
		if r == '`' {
			in = !in
			b.WriteRune(' ')
			continue
		}
		if in {
			b.WriteRune(' ')
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// paddingFloor is the number of non-blank lines below which the distinct-line
// ratio is too noisy to be evidence. A short honest file can legitimately repeat
// a single line eight times; a 200-line document that does it 100 times cannot.
const paddingFloor = 40

// paddingMinRatio is the point at which more than half the document is a repeat.
// Lowering it starts punishing boilerplate-heavy but legitimate documents
// (tables, manifests); raising it lets a document be two-thirds padding.
const paddingMinRatio = 0.5

// PaddingFindings reports an artifact whose content is mostly repetition.
//
// This is the check that catches the cheapest form of contract-gaming: paste one
// paragraph until min_bytes is satisfied. A byte count cannot distinguish that
// from a real document; a distinct-line ratio can.
func PaddingFindings(name string, content []byte) []KindResult {
	lines := strings.Split(string(content), "\n")

	seen := map[string]bool{}
	total := 0
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" {
			continue
		}
		total++
		seen[line] = true
	}
	if total < paddingFloor {
		return nil
	}

	distinct := len(seen)
	ratio := float64(distinct) / float64(total)
	if ratio >= paddingMinRatio {
		return nil
	}
	return []KindResult{{
		OK:   false,
		Code: "repetition_padding",
		Detail: fmt.Sprintf("%s has %d distinct lines out of %d non-blank (%.2f, floor %.2f)",
			name, distinct, total, ratio, paddingMinRatio),
		Hint: "replace the repeated lines with the content they were padding towards",
	}}
}

// CrossNodeDuplicates reports byte-identical artifacts produced by DIFFERENT
// nodes.
//
// Two nodes returning the same file is the strongest slop signal available: at
// least one of them did not do its own work. The same node with two identical
// artifacts is not reported, because one node legitimately mirroring a file is
// not the same claim.
//
// Empty artifacts are skipped. Two honest empty files are indistinguishable from
// each other by construction, and reporting them would make allow_empty
// unusable.
func CrossNodeDuplicates(reports []Report) []KindResult {
	type hit struct {
		nodes []string
		path  string
		bytes int64
	}
	byHash := map[string]*hit{}

	for _, r := range reports {
		for _, a := range r.Artifacts {
			if !a.OK || a.SHA256 == "" || a.Bytes == 0 {
				continue
			}
			// A glob result records "N files", not a digest. Two different file
			// sets are not the same content even when the count matches.
			if !looksLikeDigest(a.SHA256) {
				continue
			}
			h, ok := byHash[a.SHA256]
			if !ok {
				h = &hit{path: a.Path, bytes: a.Bytes}
				byHash[a.SHA256] = h
			}
			if !sliceHas(h.nodes, r.NodeID) {
				h.nodes = append(h.nodes, r.NodeID)
			}
		}
	}

	hashes := make([]string, 0, len(byHash))
	for h := range byHash {
		hashes = append(hashes, h)
	}
	sort.Strings(hashes)

	out := make([]KindResult, 0)
	for _, h := range hashes {
		v := byHash[h]
		if len(v.nodes) < 2 {
			continue
		}
		sort.Strings(v.nodes)
		out = append(out, KindResult{
			OK:   false,
			Code: "identical_artifact",
			Detail: fmt.Sprintf("nodes %s produced byte-identical artifacts (%s, %d bytes, sha256 %s)",
				strings.Join(v.nodes, ", "), v.path, v.bytes, shortDigest(h)),
			Hint: "each node must produce its own work; two nodes returning the same file means at least one did not",
		})
	}
	return out
}

func sliceHas(list []string, want string) bool {
	for _, s := range list {
		if s == want {
			return true
		}
	}
	return false
}

// looksLikeDigest reports whether a recorded value is a sha256 hex digest rather
// than a summary string such as "3 files".
func looksLikeDigest(s string) bool {
	if len(s) != 64 {
		return false
	}
	for _, r := range s {
		switch {
		case r >= '0' && r <= '9':
		case r >= 'a' && r <= 'f':
		case r >= 'A' && r <= 'F':
		default:
			return false
		}
	}
	return true
}

func shortDigest(s string) string {
	if len(s) <= 12 {
		return s
	}
	return s[:12]
}
