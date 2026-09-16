import { defineConfig } from "vitepress";

export default defineConfig({
  title: "HeliosBench",
  description: "Benchmark harness for CLI agents and terminal workflows.",
  base: "/heliosBench/",
  cleanUrls: true,
  lastUpdated: true,
  themeConfig: {
    nav: [
      { text: "Guide", link: "/guide" },
      { text: "Tasks", link: "/tasks" },
      { text: "GitHub", link: "https://github.com/KooshaPari/heliosBench" },
    ],
    sidebar: [
      {
        text: "HeliosBench",
        items: [
          { text: "Overview", link: "/" },
          { text: "Install and Run", link: "/guide" },
          { text: "Benchmark Tasks", link: "/tasks" },
        ],
      },
    ],
    socialLinks: [{ icon: "github", link: "https://github.com/KooshaPari/heliosBench" }],
  },
});
