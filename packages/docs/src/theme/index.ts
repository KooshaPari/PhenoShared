import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import AuditTimeline from './components/AuditTimeline.vue'
import BackToTop from './components/BackToTop.vue'
import Callout from './components/Callout.vue'
import CategorySwitcher from './components/CategorySwitcher.vue'
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
import '../css/custom.css'

const components = {
  AuditTimeline,
  BackToTop,
  Breadcrumb,
  Callout,
  CategorySwitcher,
  CodeAnnotation,
  CodePlayground,
  ContentTabs,
  DemoGif,
  DocStatusBadge,
  KBGraph,
  LoadingSpinner,
  ModuleSwitcher,
  NavTabs,
  OpenAPI,
  StickyHeader,
  StickySidebar,
  Toast,
  ToastContainer,
  Tooltip,
}

const theme: Theme = {
  ...DefaultTheme,
  enhanceApp({ app }) {
    for (const [name, component] of Object.entries(components)) {
      app.component(name, component)
    }
  },
  Layout: DefaultTheme.Layout,
}

export default theme

// Named exports for selective imports
export {
  AuditTimeline,
  BackToTop,
  Breadcrumb,
  Callout,
  CategorySwitcher,
  CodeAnnotation,
  CodePlayground,
  ContentTabs,
  DemoGif,
  DocStatusBadge,
  KBGraph,
  LoadingSpinner,
  ModuleSwitcher,
  NavTabs,
  OpenAPI,
  StickyHeader,
  StickySidebar,
  Toast,
  ToastContainer,
  Tooltip,
}
