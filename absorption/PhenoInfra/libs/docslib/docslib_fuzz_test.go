package docslib

import (
	"strings"
	"testing"
	"unicode/utf8"
)

func FuzzMarkdownParserParse(f *testing.F) {
	seeds := []string{
		"",
		"# Title\n\nParagraph text.",
		"## Nested Heading\n\n- list item\n\n```go\nfmt.Println(\"hi\")\n```",
		"<!-- author: docs -->\n# Metadata\n\nBody",
	}
	for _, seed := range seeds {
		f.Add(seed)
	}

	parser := NewMarkdownParser()
	f.Fuzz(func(t *testing.T, content string) {
		doc, err := parser.Parse(content)
		if err != nil {
			t.Fatalf("Parse returned unexpected error: %v", err)
		}
		if doc == nil {
			t.Fatal("Parse returned nil document")
		}
		if doc.Title == "" {
			t.Fatal("Parse returned empty title")
		}
		for _, node := range doc.Content {
			if node == nil {
				t.Fatal("Parse returned nil content node")
			}
			if node.NodeType() == "" {
				t.Fatalf("node %T returned empty NodeType", node)
			}
		}
	})
}

func FuzzHTMLRendererRender(f *testing.F) {
	seeds := []string{
		"Rendered text",
		"# Heading",
		strings.Repeat("x", 128),
		"<script>alert(1)</script>",
	}
	for _, seed := range seeds {
		f.Add(seed)
	}

	renderer := NewHTMLRenderer()
	f.Fuzz(func(t *testing.T, text string) {
		if !utf8.ValidString(text) {
			t.Skip("renderer accepts strings; skip invalid UTF-8 corpus entries")
		}

		doc := &Doc{
			Title: "Fuzz",
			Content: []Node{
				&HeadingNode{Level: 1, Content: text},
				&TextNode{Content: text},
			},
		}

		html, err := renderer.Render(doc)
		if err != nil {
			t.Fatalf("Render returned unexpected error: %v", err)
		}
		if !strings.Contains(html, "<!DOCTYPE html>") {
			t.Fatal("Render output is missing document preamble")
		}
		if !strings.Contains(html, "<title>Fuzz</title>") {
			t.Fatal("Render output is missing title")
		}
	})
}
