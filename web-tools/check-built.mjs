import fs from 'node:fs'
import path from 'node:path'
import { unzipSync } from 'fflate'
import { approvedFiles, release, safeFile, walk } from './files.mjs'
import { sha256 } from './text.mjs'

const files = approvedFiles()
const builtRoot = safeFile('docs/.vitepress/dist')
const pages = walk('docs/.vitepress/dist').filter(file => file.endsWith('.html'))
let links = 0
for (const file of pages) {
  const html = fs.readFileSync(safeFile(file), 'utf8')
  if (/data-mjx-error=/.test(html)) throw new Error(`Formula rendering error in ${file}`)
  if (/(?:[A-Za-z]:[\\/](?:Users|数学建模)[\\/]|file:\/\/(?:\/[A-Za-z]|[A-Za-z]:|localhost\/))/.test(html)) throw new Error('Private local path in generated HTML')
  for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const href = match[1].replaceAll('&amp;', '&')
    if (/^(?:https?:|mailto:|data:|#|javascript:)/.test(href)) continue
    const clean = decodeURIComponent(href.split('#')[0].split('?')[0])
    if (!clean) continue
    let target
    if (clean.startsWith('/')) {
      const base = `/${release.repository}/`
      if (!clean.startsWith(base)) throw new Error(`Invalid site base in ${file}: ${clean}`)
      target = path.join(builtRoot, clean.slice(base.length))
    } else target = path.resolve(path.dirname(safeFile(file)), clean)
    if (!target.startsWith(builtRoot)) throw new Error('Link outside build directory')
    if (target.endsWith(path.sep) || fs.existsSync(target) && fs.statSync(target).isDirectory()) target = path.join(target, 'index.html')
    if (!fs.existsSync(target)) throw new Error(`Broken built link in ${file}: ${href}`)
    links++
  }
}
const archive = fs.readFileSync(path.join(builtRoot, 'downloads', `${release.name}-v${release.version}.zip`))
const extracted = unzipSync(archive)
if (Object.keys(extracted).length !== files.length) throw new Error('Unexpected file count in Skill ZIP')
for (const file of files) {
  if (sha256(extracted[`${release.name}/${file.path}`] || new Uint8Array()) !== file.sha256) throw new Error('ZIP source mismatch')
}
console.log(`Built verification passed: ${pages.length} HTML pages, ${links} internal links/assets, ${files.length} ZIP entries.`)
