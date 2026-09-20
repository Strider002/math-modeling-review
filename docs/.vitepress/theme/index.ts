import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import PortalLayout from './PortalLayout.vue'
import './style.css'

export default { extends: DefaultTheme, Layout: () => h(PortalLayout) }
