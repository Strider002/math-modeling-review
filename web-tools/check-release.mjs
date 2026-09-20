import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { approvedFiles, release, root } from './files.mjs'

const files = approvedFiles()
const code = files.find(file => file.path === 'SKILL.md')?.text || ''
if (!code.includes(`name: ${release.name}`)) throw new Error('Skill name mismatch')
if (!files.some(file => file.path === 'LICENSE') || !files.some(file => file.path === 'LICENSE-DOCS')) throw new Error('Missing license')
const secretPatterns = [
  /-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----/,
  /\bgh[pousr]_[A-Za-z0-9]{30,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{30,}\b/,
  /\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b/,
  /(?:[A-Za-z]:[\\/](?:Users|数学建模)[\\/]|file:\/\/(?:\/[A-Za-z]|[A-Za-z]:|localhost\/))/
]
let count = 0
for (const file of files) {
  if (secretPatterns.some(re => re.test(file.text))) throw new Error(`Potential private information: ${file.path}`)
  count++
}
if (fs.existsSync(`${root}/.git`)) {
  const tracked = execFileSync('git', ['-c', `safe.directory=${root.replaceAll('\\', '/')}`, 'ls-files', '-z'], { cwd: root, encoding: 'utf8' }).split('\0').filter(Boolean)
  const exact = new Set([...release.files.map(f => f.path), 'README.md', 'CHANGELOG.md', 'publication.json', 'package.json', 'package-lock.json', '.gitignore', '.gitattributes'])
  for (const file of tracked) {
    if (!exact.has(file) && !/^(docs\/(?:\.vitepress\/|index\.md$|guide\.md$|about\.md$|figures\.md$)|web-tools\/|\.github\/workflows\/)/.test(file)) throw new Error(`Unapproved tracked file: ${file}`)
    if (/node_modules|\/dist\/|\.env(?:\.|$)|\.(?:pdf|xlsx|csv|docx|png|jpg|zip)$/i.test(file)) throw new Error(`Unexpected tracked artifact: ${file}`)
    if (secretPatterns.some(re => re.test(fs.readFileSync(`${root}/${file}`, 'utf8')))) throw new Error(`Potential private information in website source: ${file}`)
  }
  console.log(`Tracked file boundary checked: ${tracked.length}`)
}
console.log(`Release source validation passed: ${count} approved Skill files. This is not a complete security or scientific audit.`)
