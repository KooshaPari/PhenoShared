import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import AuditTimeline from './components/AuditTimeline.vue'
import BackToTop from './components/BackToTop.vue'
import Callout from './components/Callout.vue'
import CategorySwitcher from './components/CategorySwitcher.vue'
import CommitLog from './components/CommitLog.vue'
import ModuleSwitcher from './components/ModuleSwitcher.vue'
import Breadcrumb from './components/Breadcrumb.vue'
import CodeAnnotation from './components/CodeAnnotation.vue'
import CodePlayground from './components/CodePlayground.vue'
import ContentTabs from './components/ContentTabs.vue'
import DemoGif from './components/DemoGif.vue'
import DocStatusBadge from './components/DocStatusBadge.vue'
import KBGraph from './components/KBGraph.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import NavTabs from './components/NavTabs.vue'
import OpenAPI from './components/OpenAPI.vue'
import StickyHeader from './components/StickyHeader.vue'
import StickySidebar from './components/StickySidebar.vue'
import Toast from './components/Toast.vue'
import ToastContainer from './components/ToastContainer.vue'
import Tooltip from './components/Tooltip.vue'
import EcosystemHub from './components/EcosystemHub.vue'

// AT2/AT3/AT5 — accessibility baseline additions
import Layout from './components/Layout.vue'
import SkipLink from './components/SkipLink.vue'
import './custom.css'
import './a11y.css'

const theme: Theme = {
  ...DefaultTheme,
  enhanceApp({ app }) {
    app.component('AuditTimeline', AuditTimeline)
    app.component('BackToTop', BackToTop)
    app.component('Breadcrumb', Breadcrumb)
    app.component('CodeAnnotation', CodeAnnotation)
    app.component('CodePlayground', CodePlayground)
    app.component('ContentTabs', ContentTabs)
    app.component('DemoGif', DemoGif)
    app.component('CategorySwitcher', CategorySwitcher)
    app.component('CommitLog', CommitLog)
    app.component('Callout', Callout)
    app.component('DocStatusBadge', DocStatusBadge)
    app.component('ModuleSwitcher', ModuleSwitcher)
    app.component('KBGraph', KBGraph)
    app.component('LoadingSpinner', LoadingSpinner)
    app.component('NavTabs', NavTabs)
    app.component('OpenAPI', OpenAPI)
    app.component('StickyHeader', StickyHeader)
    app.component('StickySidebar', StickySidebar)
    app.component('Toast', Toast)
    app.component('ToastContainer', ToastContainer)
    app.component('Tooltip', Tooltip)
    app.component('EcosystemHub', EcosystemHub)
    // AT2 — register custom skip link so it slots above the VPDoc
    app.component('SkipLink', SkipLink)
  },
  // AT3 — replace default layout with one that injects the live region
  // and page-title announcer.
  Layout,
}

export default theme
