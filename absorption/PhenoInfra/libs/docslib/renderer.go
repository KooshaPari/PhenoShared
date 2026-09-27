package docslib

import (
	"strings"
)

// HTMLRenderer renders documents to HTML
type HTMLRenderer struct {
	Template string
}

// NewHTMLRenderer creates a new HTML renderer
func NewHTMLRenderer() *HTMLRenderer {
	return &HTMLRenderer{
		Template: defaultHTMLTemplate,
	}
}

// Render renders a Doc to HTML
func (r *HTMLRenderer) Render(doc *Doc) (string, error) {
	var sb strings.Builder

	sb.WriteString("<!DOCTYPE html>\n")
	sb.WriteString("<html>\n<head>\n")
	sb.WriteString("<meta charset=\"utf-8\">\n")
	sb.WriteString("<title>" + doc.Title + "</title>\n")
	sb.WriteString("</head>\n<body>\n")
	sb.WriteString("<h1>" + doc.Title + "</h1>\n")

	for _, node := range doc.Content {
		sb.WriteString(r.renderNode(node))
	}

	sb.WriteString("</body>\n</html>")

	return sb.String(), nil
}

func (r *HTMLRenderer) renderNode(node Node) string {
	switch n := node.(type) {
	case *HeadingNode:
		return r.renderHeading(n)
	case *TextNode:
		return r.renderText(n)
	case *CodeNode:
		return r.renderCode(n)
	case *ListNode:
		return r.renderList(n)
	default:
		return ""
	}
}

func (r *HTMLRenderer) renderHeading(n *HeadingNode) string {
	return "<h" + itoa(n.Level) + ">" + n.Content + "</h" + itoa(n.Level) + ">\n"
}

func (r *HTMLRenderer) renderText(n *TextNode) string {
	return "<p>" + n.Content + "</p>\n"
}

func (r *HTMLRenderer) renderCode(n *CodeNode) string {
	return "<pre><code class=\"" + n.Language + "\">" + n.Content + "</code></pre>\n"
}

func (r *HTMLRenderer) renderList(n *ListNode) string {
	var sb strings.Builder
	tag := "ul"
	if n.Ordered {
		tag = "ol"
	}
	sb.WriteString("<" + tag + ">\n")
	for _, item := range n.Items {
		sb.WriteString("<li>")
		for _, node := range item {
			sb.WriteString(r.renderNode(node))
		}
		sb.WriteString("</li>\n")
	}
	sb.WriteString("</" + tag + ">\n")
	return sb.String()
}

func itoa(i int) string {
	return string(rune('0' + i))
}

const defaultHTMLTemplate = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{{.Title}}</title>
<style>
body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
code { background: #f4f4f4; padding: 2px 5px; }
</style>
</head>
<body>
{{.Content}}
</body>
</html>`
