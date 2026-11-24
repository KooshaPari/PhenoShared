import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitepress'
import { resolveDocsBase } from "../../../docs-hub/.vitepress/base.config"

const docsDir = dirname(fileURLToPath(import.meta.url))
const phenodocsRoot = resolve(docsDir, '../../../../phenodocs')
const phenodocsTheme = resolve(phenodocsRoot, 'docs/.vitepress/theme/index.ts')
const docsBase = resolveDocsBase()

// Supported locales: en, zh-CN, zh-TW, fa, fa-Latn
const locales = {
  root: {
    label: "English",
    lang: "en",
    title: "4sgm",
    description: "4SGM - LangGraph + MCP Server"
  },
  "zh-CN": {
    label: "简体中文",
    lang: "zh-CN",
    title: "4sgm",
    description: "4SGM - LangGraph + MCP 服务器"
  },
  "zh-TW": {
    label: "繁體中文",
    lang: "zh-TW",
    title: "4sgm",
    description: "4SGM - LangGraph + MCP 伺服器"
  },
  fa: {
    label: "فارسی",
    lang: "fa",
    title: "4sgm",
    description: "4SGM - سرور LangGraph + MCP"
  },
  "fa-Latn": {
    label: "Pinglish",
    lang: "fa-Latn",
    title: "4sgm",
    description: "4SGM - LangGraph + MCP Server (Latin)"
  }
};

export default defineConfig({
  title: "4sgm",
  description: "4SGM - LangGraph + MCP Server",
  base: docsBase,
  locales,
  ignoreDeadLinks: true,
  vite: {
    resolve: {
      alias: {
        '@phenodocs-theme': phenodocsTheme,
      },
    },
    server: {
      fs: {
        allow: [phenodocsRoot],
      },
    },
  },
  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'API', link: '/api/' },
      {
        text: "🌐 Language",
        items: [
          { text: "English", link: "/" },
          { text: "简体中文", link: "/zh-CN/" },
          { text: "繁體中文", link: "/zh-TW/" },
          { text: "فارسی", link: "/fa/" },
          { text: "Pinglish", link: "/fa-Latn/" }
        ]
      }
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Getting Started', link: '/guide/' },
          { text: 'Architecture', link: '/guide/architecture' }
        ]
      },
      {
        text: 'API',
        items: [
          { text: 'Overview', link: '/api/' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/kooshapari/4sgm' }
    ]
  }
})
