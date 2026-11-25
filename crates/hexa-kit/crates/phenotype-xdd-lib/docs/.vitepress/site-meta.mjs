export const localeConfig = {
  root: {
    label: 'English',
    lang: 'en-US'
  },
  'zh-CN': {
    label: 'Simplified Chinese',
    lang: 'zh-CN'
  },
  'zh-TW': {
    label: 'Traditional Chinese',
    lang: 'zh-TW'
  },
  fa: {
    label: 'Persian',
    lang: 'fa-IR',
    dir: 'rtl'
  },
  'fa-Latn': {
    label: 'Persian Latin',
    lang: 'fa-Latn'
  }
}

export const nav = [
  { text: 'Guide', link: '/guide/' },
  { text: 'Reference', link: '/reference/' },
  { text: 'Architecture', link: '/reference/architecture/' }
]

export const sidebar = {
  '/guide/': [{ text: 'Guide', items: [{ text: 'Overview', link: '/guide/' }] }],
  '/reference/': [
    {
      text: 'Reference',
      items: [
        { text: 'Overview', link: '/reference/' },
        { text: 'Architecture', link: '/reference/architecture/' },
        { text: 'Property Testing', link: '/reference/property-testing/' },
        { text: 'Contract Testing', link: '/reference/contract-testing/' },
        { text: 'Mutation Testing', link: '/reference/mutation-testing/' },
        { text: 'SpecDD', link: '/reference/specdd/' }
      ]
    }
  ],
  '/zh-CN/': [{ text: 'Chinese', items: [{ text: 'Overview', link: '/zh-CN/' }] }],
  '/zh-TW/': [{ text: 'Traditional Chinese', items: [{ text: 'Overview', link: '/zh-TW/' }] }],
  '/fa/': [{ text: 'Persian', items: [{ text: 'Overview', link: '/fa/' }] }],
  '/fa-Latn/': [{ text: 'Persian Latin', items: [{ text: 'Overview', link: '/fa-Latn/' }] }]
}
