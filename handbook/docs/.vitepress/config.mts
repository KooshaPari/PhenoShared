import { defineConfig } from "vitepress";

export default defineConfig({
  title: "PhenoHandbook",
  description:
    "Patterns, anti-patterns, guidelines, and best practices for the Phenotype ecosystem",

  base: "/handbook/",
  // Historical/generated indexes contain known placeholder links. Critical routes are
  // enforced by requirements.test.ts and Playwright while that backlog is retired.
  ignoreDeadLinks: true,

  head: [
    ["link", { rel: "icon", href: "/favicon.ico" }],
    ["meta", { name: "theme-color", content: "#3c3c3c" }],
    ["meta", { name: "og:type", content: "website" }],
    ["meta", { name: "og:locale", content: "en" }],
    ["meta", { name: "og:site_name", content: "PhenoHandbook" }],
  ],

  themeConfig: {
    logo: "/logo.svg",

    nav: [
      { text: "Home", link: "/" },
      { text: "Patterns", link: "/patterns/" },
      { text: "Anti-Patterns", link: "/anti-patterns/" },
      { text: "Guidelines", link: "/guidelines/" },
      { text: "Checklists", link: "/checklists/" },
      { text: "Specs", link: "https://github.com/KooshaPari/PhenoSpecs" },
    ],

    sidebar: {
      "/patterns/": [
        {
          text: "Architecture",
          collapsed: false,
          items: [
            {
              text: "Hexagonal Architecture",
              link: "/patterns/architecture/hexagonal",
            },
            { text: "CQRS", link: "/patterns/architecture/cqrs" },
          ],
        },
        {
          text: "Async & Messaging",
          collapsed: false,
          items: [
            { text: "Event-Driven", link: "/patterns/async/event-driven" },
            { text: "Saga Pattern", link: "/patterns/async/saga" },
            { text: "Outbox Pattern", link: "/patterns/async/outbox" },
          ],
        },
        {
          text: "Auth",
          collapsed: false,
          items: [
            { text: "OAuth-PKCE Flow", link: "/patterns/auth/oauth-pkce" },
            { text: "JWT Authentication", link: "/patterns/auth/jwt" },
            { text: "API Keys", link: "/patterns/auth/api-keys" },
          ],
        },
        {
          text: "Caching",
          collapsed: false,
          items: [
            { text: "Cache-Aside", link: "/patterns/caching/cache-aside" },
          ],
        },
        {
          text: "Observability",
          collapsed: false,
          items: [
            {
              text: "Circuit Breaker",
              link: "/patterns/observability/circuit-breaker",
            },
            { text: "Retry Pattern", link: "/patterns/observability/retry" },
            {
              text: "Health Checks",
              link: "/patterns/observability/health-checks",
            },
            {
              text: "Graceful Degradation",
              link: "/patterns/observability/graceful-degradation",
            },
          ],
        },
        {
          text: "Testing",
          collapsed: false,
          items: [{ text: "BDD with Cucumber", link: "/patterns/testing/bdd" }],
        },
      ],
      "/anti-patterns/": [
        {
          text: "Anti-Patterns",
          items: [{ text: "Overview", link: "/anti-patterns/" }],
        },
      ],
      "/guidelines/": [
        {
          text: "Guidelines",
          items: [{ text: "Overview", link: "/guidelines/" }],
        },
      ],
      "/checklists/": [
        {
          text: "Checklists",
          items: [{ text: "Overview", link: "/checklists/" }],
        },
      ],
    },

    editLink: {
      pattern:
        "https://github.com/KooshaPari/PhenoHandbook/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/KooshaPari/PhenoHandbook" },
    ],

    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2024-Present Phenotype Team",
    },

    search: {
      provider: "local",
    },
  },
});
