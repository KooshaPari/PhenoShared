// OKF language adapter stub — Go reference (C08 L75).
//
// Implements the language-agnostic contract in adapters/README.md:
//
//	load(path) -> map
//	validate(doc) -> error
//	emit(doc) -> string
//
// CLI:
//
//	go run . validate <path.okf.json>
//	go run . emit <path.okf.json>
//
// Hermetic: stdlib only. Not a Harbor / agent-eval harness.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const okfDialect = "1.0"

var requiredSharedEntityTypes = []string{
	"intent",
	"acceptance",
	"constraint",
	"resource",
	"state",
	"gate",
}

var allowedRelationTypes = map[string]struct{}{
	"verified_by": {},
	"bounded_by":  {},
	"grounds":     {},
	"requires":    {},
	"asserts":     {},
}

func load(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var doc any
	if err := json.Unmarshal(raw, &doc); err != nil {
		return nil, err
	}
	obj, ok := doc.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("OKF root must be a JSON object")
	}
	return obj, nil
}

func asString(v any) (string, bool) {
	s, ok := v.(string)
	return s, ok
}

func asMap(v any) (map[string]any, bool) {
	m, ok := v.(map[string]any)
	return m, ok
}

func asSlice(v any) ([]any, bool) {
	s, ok := v.([]any)
	return s, ok
}

func validate(doc map[string]any, stem string) error {
	dialect, _ := asString(doc["okf"])
	if dialect != okfDialect {
		return fmt.Errorf("expected okf '%s', got %v", okfDialect, doc["okf"])
	}

	sourceID, ok := asString(doc["source_id"])
	if !ok || sourceID == "" {
		return fmt.Errorf("missing non-empty source_id")
	}
	if stem != "" && sourceID != stem {
		return fmt.Errorf("source_id %q must equal filename stem %q", sourceID, stem)
	}

	provenance, ok := asMap(doc["provenance"])
	if !ok {
		return fmt.Errorf("missing document provenance object")
	}
	provSID, _ := asString(provenance["source_id"])
	if provSID != sourceID {
		return fmt.Errorf("provenance.source_id must equal top-level source_id")
	}

	entitiesRaw, ok := asSlice(doc["entities"])
	if !ok {
		return fmt.Errorf("entities must be a JSON array")
	}
	if len(entitiesRaw) < 1 {
		return fmt.Errorf("entities must be non-empty")
	}

	ids := make(map[string]struct{})
	types := make(map[string]struct{})
	for _, item := range entitiesRaw {
		entity, ok := asMap(item)
		if !ok {
			return fmt.Errorf("each entity must be an object")
		}
		eid, ok := asString(entity["id"])
		if !ok || eid == "" {
			return fmt.Errorf("entity missing id")
		}
		etype, ok := asString(entity["type"])
		if !ok || etype == "" {
			return fmt.Errorf("entity %q missing type", eid)
		}
		label, ok := asString(entity["label"])
		if !ok || strings.TrimSpace(label) == "" {
			return fmt.Errorf("entity %q missing label", eid)
		}
		if _, exists := ids[eid]; exists {
			return fmt.Errorf("duplicate entity id %q", eid)
		}
		ids[eid] = struct{}{}
		types[etype] = struct{}{}
	}

	var missing []string
	for _, needed := range requiredSharedEntityTypes {
		if _, ok := types[needed]; !ok {
			missing = append(missing, needed)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("missing required shared entity types: %v", missing)
	}

	relationsRaw, ok := asSlice(doc["relations"])
	if !ok {
		return fmt.Errorf("relations must be a JSON array")
	}
	if len(relationsRaw) < 1 {
		return fmt.Errorf("relations must be non-empty")
	}

	for _, item := range relationsRaw {
		rel, ok := asMap(item)
		if !ok {
			return fmt.Errorf("each relation must be an object")
		}
		src, _ := asString(rel["source"])
		tgt, _ := asString(rel["target"])
		rtype, _ := asString(rel["type"])
		if _, ok := ids[src]; !ok {
			return fmt.Errorf("relation source %q not in entities", src)
		}
		if _, ok := ids[tgt]; !ok {
			return fmt.Errorf("relation target %q not in entities", tgt)
		}
		if _, ok := allowedRelationTypes[rtype]; !ok {
			return fmt.Errorf("relation type %q not in OKF v1.0 set", rtype)
		}
		rprov, ok := asMap(rel["provenance"])
		if !ok {
			return fmt.Errorf("relation provenance.source_id must equal top-level source_id")
		}
		rprovSID, _ := asString(rprov["source_id"])
		if rprovSID != sourceID {
			return fmt.Errorf("relation provenance.source_id must equal top-level source_id")
		}
	}
	return nil
}

func emit(doc map[string]any) (string, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(doc); err != nil {
		return "", err
	}
	// Encode already appends a trailing newline.
	return buf.String(), nil
}

func stemOf(path string) string {
	name := filepath.Base(path)
	const suffix = ".okf.json"
	if strings.HasSuffix(name, suffix) {
		return name[:len(name)-len(suffix)]
	}
	ext := filepath.Ext(name)
	return strings.TrimSuffix(name, ext)
}

func main() {
	os.Exit(run(os.Args))
}

func run(argv []string) int {
	if len(argv) != 3 || (argv[1] != "validate" && argv[1] != "emit") {
		fmt.Fprintf(os.Stderr, "usage: okf-adapter validate|emit <path.okf.json>\n")
		return 2
	}

	command, path := argv[1], argv[2]
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		fmt.Fprintf(os.Stderr, "fixture not found: %s\n", path)
		return 1
	}

	doc, err := load(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "OKF adapter error: %v\n", err)
		return 1
	}
	if err := validate(doc, stemOf(path)); err != nil {
		fmt.Fprintf(os.Stderr, "OKF adapter error: %v\n", err)
		return 1
	}

	if command == "validate" {
		sourceID, _ := asString(doc["source_id"])
		fmt.Printf("OKF validate ok: %s (source_id=%s)\n", path, sourceID)
		return 0
	}

	out, err := emit(doc)
	if err != nil {
		fmt.Fprintf(os.Stderr, "OKF adapter error: %v\n", err)
		return 1
	}
	fmt.Print(out)
	return 0
}
