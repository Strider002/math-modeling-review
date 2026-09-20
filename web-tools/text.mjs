import { createHash } from 'node:crypto'
import path from 'node:path'

export const sha256 = value => createHash('sha256').update(value).digest('hex')
export const pageId = file => `p-${createHash('sha256').update(file).digest('hex').slice(0, 16)}`
export const pageLink = file => `/content/${pageId(file)}.html`
export const pageFile = file => `content/${pageId(file)}.md`
export const titleOf = (content, file) => content.match(/^#\s+(.+)$/m)?.[1].trim() || path.posix.basename(file)

// Word segmentation plus Han bigrams keeps Chinese partial phrases discoverable.
// This function is deliberately self-contained: VitePress serializes it for the browser.
export function tokenize(text) {
  const normalized = text.normalize('NFKC').toLowerCase()
  const tokens = new Set(normalized.match(/[\p{L}\p{N}_-]+/gu) || [])
  if (typeof Intl.Segmenter === 'function') {
    for (const part of new Intl.Segmenter('zh', { granularity: 'word' }).segment(normalized)) {
      if (part.isWordLike) tokens.add(part.segment)
    }
  }
  for (const match of normalized.matchAll(/\p{Script=Han}+/gu)) {
    const chars = [...match[0]]
    for (let i = 0; i < chars.length - 1; i++) tokens.add(chars[i] + chars[i + 1])
  }
  return [...tokens]
}

// Convert TeX delimiters only in prose, leaving code and original source files intact.
export function proseTransform(markdown, transform) {
  let fence = null
  return markdown.split('\n').map(line => {
    const delimiter = line.match(/^\s*(`{3,}|~{3,})/)
    if (delimiter) {
      if (!fence) fence = delimiter[1]
      else if (delimiter[1][0] === fence[0] && delimiter[1].length >= fence.length) fence = null
      return line
    }
    if (fence) return line
    return line.split(/(`+[^`]*`+)/g).map(part => part.startsWith('`') ? part : transform(part)).join('')
  }).join('\n')
}

export function adaptMarkdown(content, file, approved) {
  let text = content.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '').replaceAll('\r\n', '\n')
  text = proseTransform(text, segment => segment
    .replaceAll('\\[', () => '$$').replaceAll('\\]', () => '$$')
    .replaceAll('\\(', '$').replaceAll('\\)', '$')
    .replace(/\{\{([^{}\n]+)\}\}/g, '&#123;&#123;$1&#125;&#125;')
    .replace(/\[([^\]\n]+)\]\(([^)\n]+)\)/g, (original, label, destination) => {
      if (/^(https?:|mailto:|#)/i.test(destination)) return original
      const [rawPath, fragment] = destination.replace(/^<|>$/g, '').split('#')
      const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(file), decodeURIComponent(rawPath.replaceAll('\\', '/'))))
      if (!approved.has(resolved)) throw new Error(`Unapproved link in ${file}: ${resolved}`)
      // Source files use several legacy heading-anchor conventions; link to the
      // checked destination page and let its generated outline provide section links.
      return `[${label}](${pageLink(resolved)})`
    }))
  return text
}

export function figureRows(markdown, guidePrefix, approved) {
  const rows = markdown.split(/\r?\n/).filter(line => line.startsWith('|') && !/^\|[-\s|]+$/.test(line)).slice(1)
  return rows.map(line => {
    const cells = line.split('|').slice(1, -1).map(s => s.trim())
    const match = cells[3]?.match(/\[([^\]]+)\]\(([^)]+)\)/)
    if (cells.length !== 4 || !match) throw new Error('Figure table schema has changed; review the mapping.')
    const target = path.posix.join(guidePrefix, match[2])
    if (!approved.has(target)) throw new Error('Figure guide is outside the approved file list.')
    return { model: cells[0], figure: cells[1], table: cells[2], group: match[1], condition: cells[3].replace(match[0], match[1]), link: pageLink(target) }
  })
}
