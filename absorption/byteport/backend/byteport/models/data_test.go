package models

import (
	"path/filepath"
	"testing"
)

// TestDescriptionOfReturnsAbsolutePath checks that descriptionOf renders the
// relative DSN into an absolute filesystem path so log lines show which file
// is actually being opened.
func TestDescriptionOfReturnsAbsolutePath(t *testing.T) {
	cases := []struct {
		name string
		dsn  string
	}{
		{"relative file", "file:./byteport.db"},
		{"legacy relative", "file:../database.db"},
		{"sqlite scheme", "sqlite:./alt.db"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := descriptionOf(tc.dsn)
			if !filepath.IsAbs(got) {
				t.Fatalf("descriptionOf(%q) = %q, want absolute path", tc.dsn, got)
			}
		})
	}
}

// TestSqliteFilePathForStripsScheme covers the documented prefixes the server
// accepts in DATABASE_URL.
func TestSqliteFilePathForStripsScheme(t *testing.T) {
	cases := []struct {
		dsn  string
		want string
	}{
		{"file:./byteport.db", "./byteport.db"},
		{"file:/var/data/x.db", "/var/data/x.db"},
		{"sqlite:///data/byteport.db", "/data/byteport.db"},
		{"sqlite:./alt.db", "./alt.db"},
		{"plain.db", "plain.db"},
		{"", ""},
	}
	for _, tc := range cases {
		t.Run(tc.dsn, func(t *testing.T) {
			got := sqliteFilePathFor(tc.dsn)
			if got != tc.want {
				t.Errorf("sqliteFilePathFor(%q) = %q, want %q", tc.dsn, got, tc.want)
			}
		})
	}
}

// TestSqliteDSNForPreservesFilePrefix checks that "file:" DSNs are handed back
// unchanged (the driver understands them) while "sqlite://" prefixes are
// normalised through sqliteFilePathFor.
func TestSqliteDSNForPreservesFilePrefix(t *testing.T) {
	cases := []struct {
		dsn  string
		want string
	}{
		{"file:./byteport.db", "file:./byteport.db"},
		{"file:/var/data/x.db", "file:/var/data/x.db"},
		{"sqlite:./alt.db", "./alt.db"},
		{"plain.db", "plain.db"},
	}
	for _, tc := range cases {
		t.Run(tc.dsn, func(t *testing.T) {
			got := sqliteDSNFor(tc.dsn)
			if got != tc.want {
				t.Errorf("sqliteDSNFor(%q) = %q, want %q", tc.dsn, got, tc.want)
			}
		})
	}
}

// TestIsPostgresDSN identifies PostgreSQL DSNs by their scheme prefix.
func TestIsPostgresDSN(t *testing.T) {
	cases := []struct {
		dsn  string
		want bool
	}{
		{"postgres://u:p@host:5432/db", true},
		{"postgresql://u:p@host/db", true},
		{"file:./byteport.db", false},
		{"sqlite:./alt.db", false},
		{"plain.db", false},
		{"", false},
	}
	for _, tc := range cases {
		t.Run(tc.dsn, func(t *testing.T) {
			if got := isPostgresDSN(tc.dsn); got != tc.want {
				t.Errorf("isPostgresDSN(%q) = %v, want %v", tc.dsn, got, tc.want)
			}
		})
	}
}
