import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import portal from './portal.json'
import { tokenize } from '../../web-tools/text.mjs'

const release = JSON.parse(readFileSync(new URL('../../publication.json', import.meta.url), 'utf8'))
const siteId = release.name
const base = `/${release.repository}/`
const site = portal.sites.find(s => s.id === siteId)!
const url = (id: string, path: string) => id === siteId ? path : `${portal.origin}/${portal.sites.find(s => s.id === id)!.repository}${path}`
function item(entry: any): any {
  if (entry.items) return { text: entry.text, collapsed: false, items: entry.items.map(item) }
  return { text: entry.text, link: url(entry.site, entry.path), target: '_self', rel: '' }
}

export default defineConfig({
  lang: 'zh-CN',
  title: site.label,
  description: site.description,
  base,
  cleanUrls: false,
  lastUpdated: false,
  head: [['meta', { name: 'theme-color', content: '#216c65' }]],
  markdown: {
    math: true,
    lineNumbers: false,
    config(md) { md.set({ html: false }) }
  },
  themeConfig: {
    siteTitle: 'Math Modeling Skills',
    nav: portal.nav.map(item),
    sidebar: portal.sidebar.map(item),
    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    sidebarMenuLabel: '导航',
    returnToTopLabel: '返回顶部',
    darkModeSwitchLabel: '外观',
    lightModeSwitchTitle: '切换到浅色',
    darkModeSwitchTitle: '切换到深色',
    skipToContentLabel: '跳到正文',
    search: {
      provider: 'local',
      options: {
        miniSearch: {
          options: { tokenize },
          searchOptions: { fuzzy: 0.2, prefix: true, combineWith: 'AND' }
        },
        translations: {
          button: { buttonText: '搜索当前 Skill', buttonAriaLabel: '搜索当前 Skill' },
          modal: {
            displayDetails: '显示详细结果', resetButtonTitle: '清空搜索',
            backButtonTitle: '关闭搜索', noResultsText: '没有找到结果',
            footer: { selectText: '选择', selectKeyAriaLabel: '回车', navigateText: '切换', navigateUpKeyAriaLabel: '向上', navigateDownKeyAriaLabel: '向下', closeText: '关闭', closeKeyAriaLabel: 'Esc' }
          }
        }
      }
    },
    socialLinks: [{ icon: 'github', link: `https://github.com/${portal.owner}/${release.repository}`, ariaLabel: '当前 Skill 的 GitHub 仓库' }],
    footer: {
      message: '原创文档 CC BY 4.0 · 软件 MIT · 非赛事官方项目',
      copyright: 'Copyright © 2026 Strider002'
    }
  }
})
