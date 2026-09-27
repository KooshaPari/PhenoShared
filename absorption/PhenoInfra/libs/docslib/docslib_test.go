package docslib

import "testing"

func TestMarkdownParser_Parse(t *testing.T) {
	parser := NewMarkdownParser()

	content := `# Title

This is a paragraph.

## Heading 2

More content.
`

	doc, err := parser.Parse(content)
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}

	if doc.Title != "Title" {
		t.Errorf("Title = %q, want %q", doc.Title, "Title")
	}

	if len(doc.Content) != 4 {
		t.Errorf("Content length = %d, want 4", len(doc.Content))
	}
}

func TestHTMLRenderer_Render(t *testing.T) {
	renderer := NewHTMLRenderer()

	doc := &Doc{
		Title: "Test",
		Content: []Node{
			&HeadingNode{Level: 1, Content: "Test"},
			&TextNode{Content: "A paragraph."},
		},
	}

	html, err := renderer.Render(doc)
	if err != nil {
		t.Fatalf("Render() error = %v", err)
	}

	if !contains(html, "<h1>Test</h1>") {
		t.Error("Rendered HTML missing heading")
	}

	if !contains(html, "<p>A paragraph.</p>") {
		t.Error("Rendered HTML missing paragraph")
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsHelper(s, substr))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
