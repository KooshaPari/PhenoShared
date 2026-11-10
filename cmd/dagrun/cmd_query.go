package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/KooshaPari/dagrun/internal/query"
)

// queryHelp documents the flag grammar. It is written out rather than derived
// from a FlagSet because the grammar (--where key=value, --order-by field,desc)
// is not expressible as a Go flag, and a help text that disagrees with the real
// parser is worse than no help at all.
const queryHelp = `dagrun query [flags]

Ask a question about an installed run and get rows back.

FLAGS
  --dir DIR                run directory (default ` + defaultDir + `)
  --where KEY=VALUE        repeatable, ANDed. Keys:
                             status=done|failed|running|pending|skipped
                             kind=SPEC|TEST|IMPL|...
                             role=impl|spec|intent|docs|...
                             owner=ID
                             artifact=SUBSTRING
                             id=GLOB
                             attempt>=N   (also = != > < <=)
  --select FIELDS          comma list of: id,status,kind,role,owner,title,
                           attempts,artifacts,progress
                           (default: id,status,kind,role,title)
  --order-by FIELD[,desc]  any --select field
  --limit N                keep the first N rows; 0 means no limit
  --json                   emit a JSON array on stdout

EXAMPLES
  dagrun query --where status=failed --select id,attempts,title
  dagrun query --where artifact=_test.go --json
  dagrun query --where attempt>=2 --order-by attempts,desc
`

// cmdQuery answers a question about a run without prose.
//
// The grammar lives in internal/query so the CLI, the MCP server and a test all
// build the same query. Only the two flags this command shares with every other
// one (--dir, --json) are handled here; everything else is the package's, so a
// typo names the allowed set instead of being silently ignored.
func cmdQuery(args []string) error {
	for _, a := range args {
		if a == "--help" || a == "-h" {
			fmt.Print(queryHelp)
			return nil
		}
	}
	dir := defaultDir
	jsonOut := false
	rest := make([]string, 0, len(args))

	for i := 0; i < len(args); i++ {
		a := args[i]
		switch {
		case a == "--dir" || a == "-dir":
			if i+1 >= len(args) {
				return fmt.Errorf("--dir needs a value")
			}
			dir = args[i+1]
			i++
		case strings.HasPrefix(a, "--dir=") || strings.HasPrefix(a, "-dir="):
			dir = a[strings.Index(a, "=")+1:]
		case a == "--json" || a == "-json":
			jsonOut = true
		default:
			rest = append(rest, a)
		}
	}

	q, err := query.Parse(rest)
	if err != nil {
		return err
	}
	rows, err := query.Run(dir, q)
	if err != nil {
		return err
	}
	return query.Render(os.Stdout, rows, q, jsonOut)
}
