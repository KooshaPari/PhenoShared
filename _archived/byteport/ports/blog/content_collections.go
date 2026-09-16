// T37: BytePort MDX-style content collections (blog posts, changelog, etc).
package blog

import (
	"embed"
	"gopkg.in/yaml.v3"
)

//go:embed content/*.md
var contentFS embed.FS

type Post struct {
	Slug        string `yaml:"slug"`
	Title       string `yaml:"title"`
	Date        string `yaml:"date"`
	Description string `yaml:"description"`
	Body        string `yaml:"-"`
}

func LoadPosts() ([]Post, error) {
	entries, err := contentFS.ReadDir("content")
	if err != nil { return nil, err }
	var posts []Post
	for _, e := range entries {
		data, err := contentFS.ReadFile("content/" + e.Name())
		if err != nil { return nil, err }
		var p Post
		if err := yaml.Unmarshal(data, &p); err != nil { return nil, err }
		posts = append(posts, p)
	}
	return posts, nil
}
