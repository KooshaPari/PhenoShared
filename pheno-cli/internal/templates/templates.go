package templates

import (
	"bytes"
	"embed"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"
	"text/template"
	"unicode"
)

//go:embed files/*
var TemplateFiles embed.FS

// templateDir is the directory inside TemplateFiles that holds the templates.
const templateDir = "files"

// templateExt is the file extension used by renderable templates.
const templateExt = ".tpl"

// staticOnlyTemplates lists embedded assets that are NOT Go text/templates and
// therefore cannot be rendered by RenderTemplate. They are consumed verbatim
// through dedicated accessors (e.g. GetStaticCliffToml) and are deliberately
// excluded from ListTemplates.
var staticOnlyTemplates = map[string]bool{
	// git-cliff configuration: contains git-cliff template syntax
	// ({{ commit.message | upper_first }}), which text/template cannot parse.
	"cliff.toml": true,
}

// TemplateContext holds the context variables for template rendering.
type TemplateContext struct {
	RepoName    string // Repository name
	Language    string // Programming language (go, rust, python, typescript)
	Registry    string // Package registry
	RiskProfile string // Risk profile (low, medium, high)
}

// RenderTemplate renders a template by name with the given context.
func RenderTemplate(name string, ctx TemplateContext) (string, error) {
	// Read the template file from the embedded FS
	data, err := TemplateFiles.ReadFile(templateDir + "/" + name + templateExt)
	if err != nil {
		return "", fmt.Errorf("failed to read template %s: %w", name, err)
	}

	// Parse and execute the template
	tmpl, err := template.New(name).Funcs(templateFuncs()).Parse(string(data))
	if err != nil {
		return "", fmt.Errorf("failed to parse template %s: %w", name, err)
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, ctx); err != nil {
		return "", fmt.Errorf("failed to render template %s: %w", name, err)
	}

	return buf.String(), nil
}

// templateFuncs returns the helper functions exposed to templates. These mirror
// the small subset of sprig helpers the embedded templates rely on.
func templateFuncs() template.FuncMap {
	return template.FuncMap{
		"title": titleCase,
	}
}

// titleCase upper-cases the first rune of every whitespace-separated word and
// leaves the remaining runes untouched.
func titleCase(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	prevIsSpace := true
	for _, r := range s {
		if prevIsSpace && !unicode.IsSpace(r) {
			b.WriteRune(unicode.ToUpper(r))
		} else {
			b.WriteRune(r)
		}
		prevIsSpace = unicode.IsSpace(r)
	}
	return b.String()
}

// ListTemplates returns the sorted list of template names that RenderTemplate
// can render. It is derived from the embedded file set so it can never drift
// out of sync with the templates on disk. Embedded assets that are not Go
// text/templates (see staticOnlyTemplates) are excluded.
func ListTemplates() []string {
	entries, err := fs.ReadDir(TemplateFiles, templateDir)
	if err != nil {
		// The embed directive guarantees this directory exists; a failure here
		// means the build is broken, and an empty list is the honest answer.
		return nil
	}

	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), templateExt) {
			continue
		}
		name := strings.TrimSuffix(path.Base(entry.Name()), templateExt)
		if staticOnlyTemplates[name] {
			continue
		}
		names = append(names, name)
	}

	sort.Strings(names)
	return names
}

// GetStaticCliffToml returns the static cliff.toml content.
func GetStaticCliffToml() string {
	return `# Configuration for git-cliff: https://git-cliff.org/
# Generates CHANGELOG from conventional commits

[changelog]
header = """
# Changelog

All notable changes to this project will be documented in this file.
"""

body = """
{%- for group, commits in commits | group_by(attribute="group") %}
## {{ group | replace(from="Features", to="✨ Features") | replace(from="Bug Fixes", to="🐛 Bug Fixes") | replace(from="Documentation", to="📚 Documentation") | replace(from="Performance", to="⚡ Performance") }}

{%- for commit in commits %}
- {% if commit.breaking %}**BREAKING** {% endif %}{{ commit.message | upper_first }} ([` + "`" + `{{ commit.id | truncate(length=7, end="") }}` + "`" + `]({{ commit.link }}))
  {%- if commit.body %}
  {{ commit.body | indent(prefix="  > ") }}
  {%- endif %}
{%- endfor %}
{%- endfor %}
"""

footer = """
---

**Release Date:** {{ now | date(format="%Y-%m-%d") }}
"""

trim = true

[git]
conventional_commits = true

commit_parsers = [
  {message = "^feat", group = "Features"},
  {message = "^fix", group = "Bug Fixes"},
  {message = "^doc", group = "Documentation"},
  {message = "^perf", group = "Performance"},
  {message = "^refactor", group = "Refactoring"},
  {message = "^test", group = "Testing"},
  {message = "^chore", skip = true},
  {message = "^ci", skip = true},
]

commit_filters = [
  {remove_if_matches = ".*skip.*changelog.*"},
]

tag_pattern = "v[0-9].*"
skip_tags = ""
sort_commits = "newest"
`
}
