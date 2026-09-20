import fs from 'node:fs'
import path from 'node:path'
import { zipSync } from 'fflate'
import { approvedFiles, release, root, safeFile, walk, writeGenerated } from './files.mjs'
import { adaptMarkdown, figureRows, pageFile, pageLink, sha256, titleOf } from './text.mjs'

const files = approvedFiles()
const approved = new Set(files.map(file => file.path))
const catalog = files.map(file => ({ path: file.path, title: titleOf(file.text, file.path), link: pageLink(file.path) }))

// Only generated files in these two fixed, checked directories are replaceable.
let removed = 0
for (const directory of ['docs/content', 'docs/public/downloads']) {
  for (const file of walk(directory)) {
    fs.unlinkSync(safeFile(file, true))
    removed++
  }
}

for (const file of files) {
  const isMarkdown = file.path.endsWith('.md')
  const language = ({ '.ps1': 'powershell', '.json': 'json', '.yaml': 'yaml' })[path.extname(file.path)] || 'text'
  const content = isMarkdown ? adaptMarkdown(file.text, file.path, approved)
    : `# ${titleOf(file.text, file.path)}\n\n以下为公开包中的原始资源。\n\n\`\`\`\`\`\`${language}\n${file.text}\n\`\`\`\`\`\`\n`
  const source = `https://github.com/Strider002/${release.repository}/blob/main/${file.path.split('/').map(encodeURIComponent).join('/')}`
  const metadata = `---\ntitle: ${JSON.stringify(titleOf(file.text, file.path))}\n---\n\n`
  writeGenerated(`docs/${pageFile(file.path)}`, `${metadata}${content}\n\n---\n\n[查看对应源文件](${source}) · [资源目录](/catalog.html)\n`)
}

const sections = release.name === 'math-modeling-library' ? [
  ['foundation', '问题、数据与基础方法', item => item.path.includes('/基础方法/')],
  ['advanced', '进阶模型与方法卡', item => item.path.includes('/进阶方法/')],
  ['delivery', '验证、交付与案例', item => /竞赛论文|项目经验|工程工具|竞赛规则/.test(item.path)],
  ['standards', '规范与任务入口', item => /规范\/|SKILL.md|AGENTS.md|阅读导航|公开版维护/.test(item.path)],
  ['sources', '来源与许可', item => /来源依据|LICENSE/.test(item.path)],
  ['tools', '工具与模板', item => /^(scripts|assets|agents)\//.test(item.path) || item.path === 'routing-manifest.yaml']
] : [
  ['audit', '科学审查与验证', item => /模型审查|通用规范/.test(item.path)],
  ['figures', '模型与论文图表', item => item.path.includes('/论文图表/')],
  ['delivery', '论文表达、交付与反例', item => /论文与交付|案例反例/.test(item.path)],
  ['standards', '任务入口', item => /SKILL.md|AGENTS.md|审查导航/.test(item.path)],
  ['sources', '方法依据、来源与许可', item => /来源依据|LICENSE/.test(item.path)],
  ['tools', '工具与模板', item => /^(scripts|assets|agents)\//.test(item.path)]
]
let catalogText = `# ${release.title} · 资源目录\n\n共 ${files.length} 个获准分发的文件。按当前问题查阅，不必一次读完整个库。非 Markdown 资源提供可阅读的源文件页。\n`
const covered = new Set()
for (const [id, title, predicate] of sections) {
  const entries = catalog.filter(item => !covered.has(item.path) && predicate(item))
  catalogText += `\n## ${title} {#${id}}\n\n`
  for (const item of entries) {
    catalogText += `- [${item.title}](${item.link})\n`
    covered.add(item.path)
  }
}
const missing = catalog.filter(item => !covered.has(item.path))
if (missing.length) throw new Error(`Uncategorized public resources: ${missing.map(i => i.path).join(', ')}`)
writeGenerated('docs/catalog.md', catalogText)

const zipEntries = Object.fromEntries(files.map(file => [`${release.name}/${file.path}`, [new Uint8Array(file.data), { mtime: new Date('2026-09-20T00:00:00Z') }]]))
const archiveName = `${release.name}-v${release.version}.zip`
const archive = zipSync(zipEntries, { level: 9 })
const digest = sha256(archive)
writeGenerated(`docs/public/downloads/${archiveName}`, archive)
writeGenerated('docs/public/downloads/SHA256SUMS.txt', `${digest}  ${archiveName}\n`)
const manifest = { name: release.name, version: release.version, archive: archiveName, sha256: digest, files: files.map(f => ({ path: f.path, sha256: f.sha256, bytes: f.data.length })) }
writeGenerated('docs/public/downloads/manifest.json', JSON.stringify(manifest, null, 2) + '\n')
writeGenerated('docs/download.md', `# 下载与使用\n\n## ${release.title} · v${release.version}\n\n[下载独立 Skill ZIP](/downloads/${archiveName}) · [校验和](/downloads/SHA256SUMS.txt) · [文件清单](/downloads/manifest.json)\n\n只包含 ${files.length} 个批准的 Skill 文件，不含网站依赖、构建缓存或 Git 历史。\n\nSHA-256：\n\n\`\`\`text\n${digest}\n\`\`\`\n\n## 安装与调用\n\n解压后保留完整的 \`${release.name}/\` 目录。项目级安装可放入 \`.agents/skills/\`，已有同名目录时先比较版本，不直接覆盖。\n\n在 Codex 对话中显式使用 \`$${release.name}\`，并说明任务与允许的动作；其他工具以其官方安装说明为准。\n\n[详细使用指南](/guide.html) · [Skill 入口](${pageLink('SKILL.md')}) · [许可证范围](${pageLink('LICENSES.md')})\n\n## 更新边界\n\n版本号对应此次公开包，原始方法、来源和当届赛事规则仍需按任务核对。独立 ZIP 不自动更新，也不自动安装任何其他 Skill 或依赖。\n`)

let figures = []
if (release.name === 'math-modeling-review') {
  const master = files.find(file => file.path === 'references/论文图表/00_模型与图表总表.md')
  figures = figureRows(master.text, 'references/论文图表', approved)
}
writeGenerated('docs/.vitepress/theme/figures.json', JSON.stringify(figures, null, 2) + '\n')
writeGenerated('.release/pages.json', JSON.stringify({ pages: catalog, zip: archiveName, sha256: digest }, null, 2) + '\n')
console.log(`${release.name}: ${files.length} approved files, ${figures.length} figure mappings, ZIP ${archive.length} bytes; replaced ${removed} generated files.`)
