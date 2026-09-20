import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { sha256 } from './text.mjs'

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
export const release = JSON.parse(fs.readFileSync(path.join(root, 'publication.json'), 'utf8'))

export function safeFile(relative, mustExist = false) {
  if (!relative || path.isAbsolute(relative) || relative.includes('\\') || relative.split('/').some(p => p === '..' || p === '.') || relative.includes(':')) throw new Error('Unsafe repository-relative path')
  const full = path.resolve(root, relative)
  if (!full.startsWith(root + path.sep)) throw new Error('Path escaped the release repository')
  let cursor = root
  if (fs.lstatSync(cursor).isSymbolicLink()) throw new Error('Repository root must not be a link')
  for (const piece of relative.split('/')) {
    cursor = path.join(cursor, piece)
    if (fs.existsSync(cursor) && fs.lstatSync(cursor).isSymbolicLink()) throw new Error('Linked release paths are not allowed')
  }
  if (mustExist && !fs.statSync(full).isFile()) throw new Error(`Missing release file: ${relative}`)
  return full
}

export function approvedFiles() {
  if (!['math-modeling-library', 'math-modeling-review'].includes(release.name)) throw new Error('Unknown publication target')
  if (!/^\d+\.\d+\.\d+$/.test(release.version)) throw new Error('Invalid release version')
  if (!Array.isArray(release.files) || !release.files.length) throw new Error('Empty public file list')
  const seen = new Set()
  return release.files.map(entry => {
    if (seen.has(entry.path.toLowerCase())) throw new Error('Duplicate file in public list')
    seen.add(entry.path.toLowerCase())
    const data = fs.readFileSync(safeFile(entry.path, true))
    if (sha256(data) !== entry.sha256.toLowerCase()) throw new Error(`Source changed; review before release: ${entry.path}`)
    return { ...entry, data, text: data.toString('utf8') }
  })
}

export function writeGenerated(relative, contents) {
  const target = safeFile(relative)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.writeFileSync(target, contents)
}

export function walk(relative) {
  const target = safeFile(relative)
  if (!fs.existsSync(target)) return []
  return fs.readdirSync(target, { withFileTypes: true }).flatMap(entry => {
    const child = `${relative}/${entry.name}`
    safeFile(child)
    if (entry.isSymbolicLink()) throw new Error('Linked generated artifact is not allowed')
    return entry.isDirectory() ? walk(child) : [child]
  })
}
