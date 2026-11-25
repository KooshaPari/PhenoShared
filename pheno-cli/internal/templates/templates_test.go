package templates

import (
	"io/fs"
	"sort"
	"strings"
	"testing"
)

func TestRenderTemplate(t *testing.T) {
	languages := []string{"go", "rust", "python", "typescript"}

	for _, lang := range languages {
		t.Run(lang, func(t *testing.T) {
			ctx := TemplateContext{
				RepoName:    "test-repo",
				Language:    lang,
				Registry:    "npm",
				RiskProfile: "low",
			}

			// Test mise.toml template
			result, err := RenderTemplate("mise.toml", ctx)
			if err != nil {
				t.Fatalf("failed to render mise.toml for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "[tasks.") {
				t.Fatal("rendered template missing expected content")
			}

			// Test pre-commit.sh template
			result, err = RenderTemplate("pre-commit.sh", ctx)
			if err != nil {
				t.Fatalf("failed to render pre-commit.sh for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "Conventional commit") {
				t.Fatal("rendered template missing expected content")
			}

			// Test ci.yml template
			result, err = RenderTemplate("ci.yml", ctx)
			if err != nil {
				t.Fatalf("failed to render ci.yml for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "name: CI") {
				t.Fatal("rendered template missing CI workflow name")
			}
		})
	}
}

func TestRenderTemplate_InvalidName(t *testing.T) {
	ctx := TemplateContext{
		RepoName:    "test-repo",
		Language:    "go",
		Registry:    "npm",
		RiskProfile: "low",
	}

	_, err := RenderTemplate("nonexistent", ctx)
	if err == nil {
		t.Fatal("expected error for nonexistent template")
	}
}

func TestListTemplates(t *testing.T) {
	templates := ListTemplates()

	if len(templates) == 0 {
		t.Fatal("expected at least one template, got none")
	}

	// ListTemplates must be sorted and free of duplicates/empties, otherwise
	// callers cannot rely on it for deterministic discovery.
	if !sort.StringsAreSorted(templates) {
		t.Fatalf("ListTemplates result is not sorted: %v", templates)
	}
	for i, name := range templates {
		if name == "" {
			t.Fatalf("ListTemplates returned an empty name at index %d", i)
		}
		if strings.HasSuffix(name, templateExt) {
			t.Fatalf("ListTemplates returned %q with a %s suffix; names are bare", name, templateExt)
		}
		if i > 0 && templates[i-1] == name {
			t.Fatalf("ListTemplates returned duplicate template %q", name)
		}
	}

	// Every advertised template must actually render.
	ctx := TemplateContext{
		RepoName:    "test-repo",
		Language:    "go",
		Registry:    "npm",
		RiskProfile: "low",
	}
	for _, name := range templates {
		out, err := RenderTemplate(name, ctx)
		if err != nil {
			t.Fatalf("ListTemplates advertised %q but it failed to render: %v", name, err)
		}
		if len(out) == 0 {
			t.Fatalf("advertised template %q rendered empty", name)
		}
	}

	// ListTemplates must cover every embedded renderable template, so a newly
	// added files/*.tpl can never be silently hidden from discovery.
	entries, err := fs.ReadDir(TemplateFiles, templateDir)
	if err != nil {
		t.Fatalf("failed to read embedded %s dir: %v", templateDir, err)
	}
	listed := make(map[string]bool, len(templates))
	for _, name := range templates {
		listed[name] = true
	}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), templateExt) {
			continue
		}
		name := strings.TrimSuffix(entry.Name(), templateExt)
		if staticOnlyTemplates[name] {
			continue
		}
		if !listed[name] {
			t.Errorf("embedded template %q is missing from ListTemplates", name)
		}
	}

	// The bootstrap pipeline (cmd/bootstrap.go, internal/rollout) hard-codes
	// these template names, so they must always remain available.
	for _, name := range []string{
		"mise.toml",
		"pre-commit.sh",
		"pre-push.sh",
		"ci.yml",
		"release.yml",
	} {
		found := false
		for _, have := range templates {
			if have == name {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("bootstrap template %q is missing from ListTemplates", name)
		}
	}
}
