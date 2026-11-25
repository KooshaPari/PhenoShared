package verify

import (
	"strings"
	"testing"
)

func codes(rs []KindResult) []string {
	out := make([]string, 0, len(rs))
	for _, r := range rs {
		out = append(out, r.Code)
	}
	return out
}

func TestPlaceholderFindings(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		wantHits int
		wantCode string
	}{
		{
			name:     "marker at the start of a file",
			content:  "TODO: write this section\n",
			wantHits: 1,
			wantCode: "placeholder_marker",
		},
		{
			name:     "marker deep in a file reports its line",
			content:  "line one\nline two\nTBD\n",
			wantHits: 1,
			wantCode: "placeholder_marker",
		},
		{
			name:     "lowercase is still a marker",
			content:  "this section is a placeholder for later\n",
			wantHits: 1,
			wantCode: "placeholder_marker",
		},
		{
			name:     "fenced code block is quoted, not slop",
			content:  "Here is the rule:\n\n```\nTODO: write the content\n```\n\nAnd that is the rule.\n",
			wantHits: 0,
		},
		{
			name:     "inline backticks are quoted, not slop",
			content:  "The linter rejects `TODO` and `FIXME` markers.\n",
			wantHits: 0,
		},
		{
			name:     "a word containing the marker is not the marker",
			content:  "const TODO_LIST_SIZE = 10\n",
			wantHits: 0,
		},
		{
			name:     "a clean document has no findings",
			content:  "This document was actually written.\nIt has content in it.\n",
			wantHits: 0,
		},
		{
			name:     "two different markers produce two findings",
			content:  "TODO here\nFIXME there\n",
			wantHits: 2,
			wantCode: "placeholder_marker",
		},
		{
			name:     "the same marker twice produces one finding",
			content:  "TODO here\nTODO again\n",
			wantHits: 1,
			wantCode: "placeholder_marker",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := PlaceholderFindings("art.md", []byte(tc.content))
			if len(got) != tc.wantHits {
				t.Fatalf("got %d findings (%v), want %d", len(got), codes(got), tc.wantHits)
			}
			for _, f := range got {
				if f.OK {
					t.Error("a finding must not be OK")
				}
				if tc.wantCode != "" && f.Code != tc.wantCode {
					t.Errorf("code = %q, want %q", f.Code, tc.wantCode)
				}
				if f.Detail == "" || f.Hint == "" {
					t.Errorf("a finding without a detail and a hint is not actionable: %+v", f)
				}
			}
		})
	}
}

func TestPaddingFindings(t *testing.T) {
	repeat := func(line string, n int) string {
		var b strings.Builder
		for i := 0; i < n; i++ {
			b.WriteString(line)
			b.WriteString("\n")
		}
		return b.String()
	}

	tests := []struct {
		name     string
		content  string
		wantHits int
	}{
		{
			name:     "one paragraph pasted 50 times over 100 lines is padding",
			content:  repeat("the same sentence repeated to satisfy min_bytes", 100),
			wantHits: 1,
		},
		{
			name:     "a short repetitive file is below the floor and is not punished",
			content:  repeat("same line", 20),
			wantHits: 0,
		},
		{
			name:     "a normal document of 200 distinct lines is clean",
			content:  strings.Repeat("", 0) + manyDistinctLines(200),
			wantHits: 0,
		},
		{
			name:     "exactly at the floor with high repetition is flagged",
			content:  repeat("identical", paddingFloor),
			wantHits: 1,
		},
		{
			name:     "one line below the floor is not flagged",
			content:  repeat("identical", paddingFloor-1),
			wantHits: 0,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := PaddingFindings("art.md", []byte(tc.content))
			if len(got) != tc.wantHits {
				t.Fatalf("got %d findings (%v), want %d", len(got), codes(got), tc.wantHits)
			}
			if tc.wantHits > 0 && got[0].Code != "repetition_padding" {
				t.Errorf("code = %q, want repetition_padding", got[0].Code)
			}
		})
	}
}

// manyDistinctLines builds a document with no repetition, so the ratio is 1.0.
func manyDistinctLines(n int) string {
	var b strings.Builder
	for i := 0; i < n; i++ {
		b.WriteString("distinct line number ")
		b.WriteString(itoa(i))
		b.WriteString("\n")
	}
	return b.String()
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var digits []byte
	for i > 0 {
		digits = append([]byte{byte('0' + i%10)}, digits...)
		i /= 10
	}
	return string(digits)
}

const digestA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
const digestB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

func TestCrossNodeDuplicates(t *testing.T) {
	tests := []struct {
		name     string
		reports  []Report
		wantHits int
	}{
		{
			name: "two different nodes with the same content are flagged",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
			},
			wantHits: 1,
		},
		{
			name: "one node with two identical artifacts is not flagged",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{
					{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12},
					{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12},
				}},
			},
			wantHits: 0,
		},
		{
			name: "two empty artifacts are not flagged",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 0}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 0}}},
			},
			wantHits: 0,
		},
		{
			name: "a glob summary is not a digest",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "*.go", OK: true, SHA256: "3 files", Bytes: 90}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "*.go", OK: true, SHA256: "3 files", Bytes: 90}}},
			},
			wantHits: 0,
		},
		{
			name: "a failed artifact is not evidence of duplication",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: false, SHA256: digestA, Bytes: 12}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
			},
			wantHits: 0,
		},
		{
			name: "three nodes sharing content produce one finding naming all three",
			reports: []Report{
				{NodeID: "3", Artifacts: []ArtifactResult{{Path: "c.md", OK: true, SHA256: digestA, Bytes: 12}}},
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
			},
			wantHits: 1,
		},
		{
			name: "two distinct digests shared by two pairs produce two findings",
			reports: []Report{
				{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12}}},
				{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
				{NodeID: "3", Artifacts: []ArtifactResult{{Path: "c.md", OK: true, SHA256: digestB, Bytes: 9}}},
				{NodeID: "4", Artifacts: []ArtifactResult{{Path: "d.md", OK: true, SHA256: digestB, Bytes: 9}}},
			},
			wantHits: 2,
		},
		{
			name:     "no reports means no findings",
			reports:  nil,
			wantHits: 0,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := CrossNodeDuplicates(tc.reports)
			if len(got) != tc.wantHits {
				t.Fatalf("got %d findings (%v), want %d", len(got), codes(got), tc.wantHits)
			}
			for _, f := range got {
				if f.Code != "identical_artifact" {
					t.Errorf("code = %q, want identical_artifact", f.Code)
				}
				if f.Hint == "" {
					t.Error("a finding without a hint is not actionable")
				}
			}
		})
	}
}

// The finding must name every node involved, because naming one leaves the
// reader guessing which of the others is the copy.
func TestCrossNodeDuplicatesNamesEveryNode(t *testing.T) {
	got := CrossNodeDuplicates([]Report{
		{NodeID: "3", Artifacts: []ArtifactResult{{Path: "c.md", OK: true, SHA256: digestA, Bytes: 12}}},
		{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12}}},
		{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
	})
	if len(got) != 1 {
		t.Fatalf("got %d findings, want 1", len(got))
	}
	for _, id := range []string{"1", "2", "3"} {
		if !strings.Contains(got[0].Detail, id) {
			t.Errorf("detail does not name node %s: %s", id, got[0].Detail)
		}
	}
}

// Determinism: the same input must produce the same output order, or a diff
// between two runs shows changes that did not happen.
func TestCrossNodeDuplicatesIsDeterministic(t *testing.T) {
	in := []Report{
		{NodeID: "4", Artifacts: []ArtifactResult{{Path: "d.md", OK: true, SHA256: digestB, Bytes: 9}}},
		{NodeID: "2", Artifacts: []ArtifactResult{{Path: "b.md", OK: true, SHA256: digestA, Bytes: 12}}},
		{NodeID: "3", Artifacts: []ArtifactResult{{Path: "c.md", OK: true, SHA256: digestB, Bytes: 9}}},
		{NodeID: "1", Artifacts: []ArtifactResult{{Path: "a.md", OK: true, SHA256: digestA, Bytes: 12}}},
	}
	first := CrossNodeDuplicates(in)
	for i := 0; i < 5; i++ {
		again := CrossNodeDuplicates(in)
		for j := range first {
			if first[j].Code != again[j].Code || first[j].Detail != again[j].Detail {
				t.Fatalf("output changed between runs at %d", j)
			}
		}
	}
}
