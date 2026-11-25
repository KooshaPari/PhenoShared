package docslib

import (
	"os"
	"strings"
)

// MarkdownParser parses Markdown documents
type MarkdownParser struct{}

// NewMarkdownParser creates a new Markdown parser
func NewMarkdownParser() *MarkdownParser {
	return &MarkdownParser{}
}

// Parse parses Markdown content into a Doc
func (p *MarkdownParser) Parse(content string) (*Doc, error) {
	lines := strings.Split(content, "\n")

	doc := &Doc{
		Title:   extractTitle(lines),
		Content: p.parseNodes(lines),
		Meta:    extractMetadata(lines),
	}

	return doc, nil
}

func (p *MarkdownParser) parseNodes(lines []string) []Node {
	var nodes []Node

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		if strings.HasPrefix(line, "#") {
			level := len(line) - len(strings.TrimLeft(line, "#"))
			nodes = append(nodes, &HeadingNode{
				Level:   level,
				Content: strings.TrimSpace(line[level:]),
			})
		} else {
			nodes = append(nodes, &TextNode{Content: line})
		}
	}

	return nodes
}

func extractTitle(lines []string) string {
	for _, line := range lines {
		if strings.HasPrefix(line, "# ") {
			title := strings.TrimSpace(line[2:])
			if title != "" {
				return title
			}
		}
	}
	return "Untitled"
}

func extractMetadata(lines []string) Metadata {
	meta := Metadata{}

	for _, line := range lines {
		if strings.HasPrefix(line, "<!--") && strings.HasSuffix(line, "-->") {
			// Parse frontmatter-style metadata
		}
	}

	return meta
}

func (p *MarkdownParser) ParseFile(path string) (*Doc, error) {
	content, err := ReadFile(path)
	if err != nil {
		return nil, err
	}
	return p.Parse(content)
}

// ReadFile reads a file
func ReadFile(path string) (string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(content), nil
}
